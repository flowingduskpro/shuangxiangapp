import { Test, TestingModule } from '@nestjs/testing';
import { INestApplication } from '@nestjs/common';
import { AppModule } from '../src/app.module';
import { PrismaService } from '../src/database/prisma.service';
import { RedisService } from '../src/database/redis.service';
import { JwtService } from '@nestjs/jwt';
import { io, Socket } from 'socket.io-client';

describe('WebSocket Integration Tests', () => {
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
    await app.listen(3001);

    prismaService = moduleFixture.get<PrismaService>(PrismaService);
    redisService = moduleFixture.get<RedisService>(RedisService);
    jwtService = moduleFixture.get<JwtService>(JwtService);

    // Generate a test JWT token
    token = jwtService.sign({
      sub: 'test-user-1',
      role: 'student',
      class_id: 'test-class-1',
    });

    // Create a test class session
    const session = await prismaService.classSession.create({
      data: {
        classId: 'test-class-1',
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
    client = io('http://localhost:3001', {
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

  describe('Authentication', () => {
    it('should authenticate with valid JWT token', (done) => {
      client.connect();
      
      client.on('connect', () => {
        client.emit('auth', { token }, (response) => {
          expect(response.status).toBe('success');
          expect(response.correlation_id).toBeDefined();
          done();
        });
      });
    });

    it('should fail authentication with invalid token', (done) => {
      client.connect();
      
      client.on('connect', () => {
        client.emit('auth', { token: 'invalid-token' }, (response) => {
          expect(response.status).toBe('error');
          expect(response.message).toBe('Authentication failed');
          done();
        });
      });
    });
  });

  describe('Join Class Session', () => {
    it('should successfully join a class session after auth', (done) => {
      client.connect();
      
      client.on('connect', () => {
        client.emit('auth', { token }, (authResponse) => {
          expect(authResponse.status).toBe('success');
          
          client.emit('join_class_session', 
            { class_session_id: classSessionId }, 
            (joinResponse) => {
              expect(joinResponse.status).toBe('success');
              expect(joinResponse.correlation_id).toBeDefined();
              done();
            }
          );
        });
      });
    });

    it('should receive aggregate update after joining', (done) => {
      client.connect();
      
      client.on('class_session_aggregate', (aggregate) => {
        expect(aggregate.class_session_id).toBe(classSessionId);
        expect(aggregate.joined_count).toBeGreaterThanOrEqual(1);
        expect(aggregate.version).toBe('v1');
        done();
      });

      client.on('connect', () => {
        client.emit('auth', { token });
        setTimeout(() => {
          client.emit('join_class_session', { class_session_id: classSessionId });
        }, 100);
      });
    }, 10000);

    it('should fail to join without authentication', (done) => {
      client.connect();
      
      client.on('connect', () => {
        client.emit('join_class_session', 
          { class_session_id: classSessionId }, 
          (response) => {
            expect(response.status).toBe('error');
            expect(response.message).toBe('Not authenticated');
            done();
          }
        );
      });
    });
  });
});
