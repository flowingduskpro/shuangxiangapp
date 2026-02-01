import { Test, TestingModule } from '@nestjs/testing';
import { INestApplication } from '@nestjs/common';
import { AppModule } from '../src/app.module';
import { PrismaService } from '../src/database/prisma.service';
import { RedisService } from '../src/database/redis.service';
import { JwtService } from '@nestjs/jwt';
import { io, Socket } from 'socket.io-client';

describe('Event Recording Integration Tests', () => {
  let app: INestApplication;
  let prismaService: PrismaService;
  let redisService: RedisService;
  let jwtService: JwtService;
  let client: Socket;
  let token: string;
  let classSessionId: string;

  beforeAll(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({
      imports: [AppModule],
    }).compile();

    app = moduleFixture.createNestApplication();
    await app.init();
    await app.listen(3002);

    prismaService = moduleFixture.get<PrismaService>(PrismaService);
    redisService = moduleFixture.get<RedisService>(RedisService);
    jwtService = moduleFixture.get<JwtService>(JwtService);

    token = jwtService.sign({
      sub: 'test-user-2',
      role: 'student',
      class_id: 'test-class-2',
    });

    const session = await prismaService.classSession.create({
      data: {
        classId: 'test-class-2',
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

  beforeEach(() => {
    client = io('http://localhost:3002', {
      transports: ['websocket'],
      autoConnect: false,
    });
  });

  afterEach((done) => {
    if (client.connected) {
      client.disconnect();
    }
    done();
  });

  describe('class_enter Event', () => {
    it('should record event in PostgreSQL', (done) => {
      client.connect();

      client.on('connect', async () => {
        client.emit('auth', { token });
        await new Promise(resolve => setTimeout(resolve, 100));
        
        client.emit('join_class_session', { class_session_id: classSessionId });
        await new Promise(resolve => setTimeout(resolve, 100));
        
        client.emit('event', 
          { event_type: 'class_enter', event_data: { timestamp: Date.now() } }, 
          async (response) => {
            expect(response.status).toBe('success');
            
            // Verify event is in database
            const events = await prismaService.classEvent.findMany({
              where: { classSessionId, eventType: 'class_enter' },
            });
            
            expect(events.length).toBeGreaterThanOrEqual(1);
            expect(events[0].userId).toBe('test-user-2');
            expect(events[0].correlationId).toBe(response.correlation_id);
            done();
          }
        );
      });
    }, 10000);

    it('should increment enter_event_count in Redis', (done) => {
      client.connect();

      client.on('connect', async () => {
        client.emit('auth', { token });
        await new Promise(resolve => setTimeout(resolve, 100));
        
        client.emit('join_class_session', { class_session_id: classSessionId });
        await new Promise(resolve => setTimeout(resolve, 100));
        
        const initialCount = await redisService.get(`session:${classSessionId}:enter_count`);
        const initial = initialCount ? parseInt(initialCount, 10) : 0;
        
        client.emit('event', 
          { event_type: 'class_enter' }, 
          async (response) => {
            expect(response.status).toBe('success');
            
            const finalCount = await redisService.get(`session:${classSessionId}:enter_count`);
            const final = finalCount ? parseInt(finalCount, 10) : 0;
            
            expect(final).toBe(initial + 1);
            done();
          }
        );
      });
    }, 10000);

    it('should send aggregate update within 1 second', (done) => {
      const startTime = Date.now();
      client.connect();

      client.on('class_session_aggregate', (aggregate) => {
        const elapsed = Date.now() - startTime;
        expect(elapsed).toBeLessThan(1000);
        expect(aggregate.enter_event_count).toBeGreaterThanOrEqual(1);
        done();
      });

      client.on('connect', async () => {
        client.emit('auth', { token });
        await new Promise(resolve => setTimeout(resolve, 100));
        client.emit('join_class_session', { class_session_id: classSessionId });
        await new Promise(resolve => setTimeout(resolve, 100));
        client.emit('event', { event_type: 'class_enter' });
      });
    }, 10000);

    it('should reject unsupported event types', (done) => {
      client.connect();

      client.on('connect', async () => {
        client.emit('auth', { token });
        await new Promise(resolve => setTimeout(resolve, 100));
        client.emit('join_class_session', { class_session_id: classSessionId });
        await new Promise(resolve => setTimeout(resolve, 100));
        
        client.emit('event', 
          { event_type: 'unsupported_event' }, 
          (response) => {
            expect(response.status).toBe('error');
            expect(response.message).toBe('Unsupported event type');
            done();
          }
        );
      });
    }, 10000);
  });
});
