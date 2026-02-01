import { Test, TestingModule } from '@nestjs/testing';
import { INestApplication } from '@nestjs/common';
import { AppModule } from '../src/app.module';
import { PrismaService } from '../src/database/prisma.service';
import { RedisService } from '../src/database/redis.service';
import { JwtService } from '@nestjs/jwt';
import { io, Socket } from 'socket.io-client';

describe('Aggregation Integration Tests', () => {
  let app: INestApplication;
  let prismaService: PrismaService;
  let redisService: RedisService;
  let jwtService: JwtService;
  let token1: string;
  let token2: string;
  let classSessionId: string;

  beforeAll(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({
      imports: [AppModule],
    }).compile();

    app = moduleFixture.createNestApplication();
    await app.init();
    await app.listen(3003);

    prismaService = moduleFixture.get<PrismaService>(PrismaService);
    redisService = moduleFixture.get<RedisService>(RedisService);
    jwtService = moduleFixture.get<JwtService>(JwtService);

    token1 = jwtService.sign({
      sub: 'test-user-3',
      role: 'student',
      class_id: 'test-class-3',
    });

    token2 = jwtService.sign({
      sub: 'test-user-4',
      role: 'student',
      class_id: 'test-class-3',
    });

    const session = await prismaService.classSession.create({
      data: {
        classId: 'test-class-3',
        status: 'active',
      },
    });
    classSessionId = session.id;
  });

  afterAll(async () => {
    await prismaService.classEvent.deleteMany({});
    await prismaService.classSession.deleteMany({});
    const keys = await redisService.getClient().keys('session:*');
    if (keys.length > 0) {
      await redisService.getClient().del(...keys);
    }
    await app.close();
  });

  describe('Single Connection Scenario', () => {
    let client: Socket;

    beforeEach(() => {
      client = io('http://localhost:3003', {
        transports: ['websocket'],
        autoConnect: false,
      });
    });

    afterEach((done) => {
      if (client.connected) {
        client.disconnect();
      }
      setTimeout(done, 100);
    });

    it('should have joined_count == 1 and enter_event_count == 1', (done) => {
      client.connect();

      client.on('class_session_aggregate', (aggregate) => {
        if (aggregate.enter_event_count === 1) {
          expect(aggregate.joined_count).toBe(1);
          expect(aggregate.enter_event_count).toBe(1);
          done();
        }
      });

      client.on('connect', async () => {
        client.emit('auth', { token: token1 });
        await new Promise(resolve => setTimeout(resolve, 100));
        client.emit('join_class_session', { class_session_id: classSessionId });
        await new Promise(resolve => setTimeout(resolve, 100));
        client.emit('event', { event_type: 'class_enter' });
      });
    }, 15000);
  });

  describe('Dual Connection Scenario', () => {
    let client1: Socket;
    let client2: Socket;

    beforeEach(() => {
      client1 = io('http://localhost:3003', {
        transports: ['websocket'],
        autoConnect: false,
      });
      client2 = io('http://localhost:3003', {
        transports: ['websocket'],
        autoConnect: false,
      });
    });

    afterEach((done) => {
      if (client1.connected) client1.disconnect();
      if (client2.connected) client2.disconnect();
      setTimeout(done, 200);
    });

    it('should have joined_count == 2 and enter_event_count == 2', (done) => {
      let aggregateCount = 0;

      const checkAggregate = (aggregate) => {
        aggregateCount++;
        if (aggregate.enter_event_count === 2) {
          expect(aggregate.joined_count).toBe(2);
          expect(aggregate.enter_event_count).toBe(2);
          done();
        }
      };

      client1.on('class_session_aggregate', checkAggregate);
      client2.on('class_session_aggregate', checkAggregate);

      client1.connect();
      client1.on('connect', async () => {
        client1.emit('auth', { token: token1 });
        await new Promise(resolve => setTimeout(resolve, 100));
        client1.emit('join_class_session', { class_session_id: classSessionId });
        await new Promise(resolve => setTimeout(resolve, 100));
        client1.emit('event', { event_type: 'class_enter' });
        
        // Start second client
        await new Promise(resolve => setTimeout(resolve, 200));
        client2.connect();
      });

      client2.on('connect', async () => {
        client2.emit('auth', { token: token2 });
        await new Promise(resolve => setTimeout(resolve, 100));
        client2.emit('join_class_session', { class_session_id: classSessionId });
        await new Promise(resolve => setTimeout(resolve, 100));
        client2.emit('event', { event_type: 'class_enter' });
      });
    }, 20000);
  });

  describe('Idempotency', () => {
    let client: Socket;

    beforeEach(() => {
      client = io('http://localhost:3003', {
        transports: ['websocket'],
        autoConnect: false,
      });
    });

    afterEach((done) => {
      if (client.connected) {
        client.disconnect();
      }
      setTimeout(done, 100);
    });

    it('should not increase joined_count on repeated joins', (done) => {
      client.connect();
      let firstJoinCount: number;

      client.on('class_session_aggregate', (aggregate) => {
        if (!firstJoinCount) {
          firstJoinCount = aggregate.joined_count;
          // Try joining again
          setTimeout(() => {
            client.emit('join_class_session', { class_session_id: classSessionId });
          }, 100);
        } else {
          // Second aggregate after rejoining
          expect(aggregate.joined_count).toBe(firstJoinCount);
          done();
        }
      });

      client.on('connect', async () => {
        client.emit('auth', { token: token1 });
        await new Promise(resolve => setTimeout(resolve, 100));
        client.emit('join_class_session', { class_session_id: classSessionId });
      });
    }, 15000);
  });
});
