const io = require('socket.io-client');
const jwt = require('jsonwebtoken');

const SERVER_URL = process.env.SERVER_URL || 'http://localhost:3000';
const JWT_SECRET = process.env.JWT_SECRET || 'dev-secret-change-in-production';
const CLASS_SESSION_ID = process.env.CLASS_SESSION_ID;

if (!CLASS_SESSION_ID) {
  console.error('ERROR: CLASS_SESSION_ID environment variable is required');
  process.exit(1);
}

// Generate test JWT token
const token = jwt.sign(
  {
    sub: 'e2e-test-user',
    role: 'student',
    class_id: 'e2e-test-class',
  },
  JWT_SECRET,
  {
    issuer: 'shuangxiang-app',
    expiresIn: '1h',
  }
);

console.log('Starting E2E WebSocket Test Client...');
console.log(`Server: ${SERVER_URL}`);
console.log(`Class Session ID: ${CLASS_SESSION_ID}`);

const client = io(SERVER_URL, {
  transports: ['websocket'],
});

const testResults = {
  auth: { success: false, time: 0 },
  join: { success: false, time: 0 },
  event: { success: false, time: 0 },
  ack: { received: false, time: 0 },
  aggregate: { received: false, time: 0, data: null },
};

let authTime, eventTime;

client.on('connect', () => {
  console.log('[CONNECTED] Client connected to server');
  
  // Step 1: Authenticate
  authTime = Date.now();
  client.emit('auth', { token }, (response) => {
    testResults.auth.time = Date.now() - authTime;
    testResults.auth.success = response.status === 'success';
    
    console.log(`[AUTH] ${response.status.toUpperCase()} - Time: ${testResults.auth.time}ms`);
    console.log(`[AUTH] Correlation ID: ${response.correlation_id}`);
    
    if (testResults.auth.success) {
      // Step 2: Join class session
      const joinTime = Date.now();
      client.emit('join_class_session', { class_session_id: CLASS_SESSION_ID }, (joinResponse) => {
        testResults.join.time = Date.now() - joinTime;
        testResults.join.success = joinResponse.status === 'success';
        
        console.log(`[JOIN] ${joinResponse.status.toUpperCase()} - Time: ${testResults.join.time}ms`);
        console.log(`[JOIN] Correlation ID: ${joinResponse.correlation_id}`);
        
        if (testResults.join.success) {
          // Step 3: Send class_enter event
          setTimeout(() => {
            eventTime = Date.now();
            client.emit('event', 
              { event_type: 'class_enter', event_data: { test: true } }, 
              (eventResponse) => {
                testResults.event.time = Date.now() - eventTime;
                testResults.event.success = eventResponse.status === 'success';
                testResults.ack.received = true;
                testResults.ack.time = testResults.event.time;
                
                console.log(`[EVENT] ${eventResponse.status.toUpperCase()} - Time: ${testResults.event.time}ms`);
                console.log(`[ACK] Received in ${testResults.ack.time}ms`);
                console.log(`[ACK] Correlation ID: ${eventResponse.correlation_id}`);
                
                // Wait for aggregate
                setTimeout(() => {
                  printResults();
                  client.disconnect();
                }, 2000);
              }
            );
          }, 500);
        }
      });
    }
  });
});

client.on('class_session_aggregate', (aggregate) => {
  if (!testResults.aggregate.received) {
    testResults.aggregate.received = true;
    testResults.aggregate.time = Date.now() - eventTime;
    testResults.aggregate.data = aggregate;
    
    console.log(`[AGGREGATE] Received in ${testResults.aggregate.time}ms`);
    console.log(`[AGGREGATE] Data:`, JSON.stringify(aggregate, null, 2));
  }
});

client.on('disconnect', () => {
  console.log('[DISCONNECTED] Client disconnected from server');
});

client.on('error', (error) => {
  console.error('[ERROR]', error);
});

function printResults() {
  console.log('\n=== E2E Test Results ===');
  console.log(`✓ Auth: ${testResults.auth.success ? 'PASS' : 'FAIL'} (${testResults.auth.time}ms)`);
  console.log(`✓ Join: ${testResults.join.success ? 'PASS' : 'FAIL'} (${testResults.join.time}ms)`);
  console.log(`✓ Event: ${testResults.event.success ? 'PASS' : 'FAIL'} (${testResults.event.time}ms)`);
  console.log(`✓ ACK received: ${testResults.ack.received ? 'PASS' : 'FAIL'} (${testResults.ack.time}ms)`);
  console.log(`✓ ACK within 1s: ${testResults.ack.time < 1000 ? 'PASS' : 'FAIL'}`);
  console.log(`✓ Aggregate received: ${testResults.aggregate.received ? 'PASS' : 'FAIL'} (${testResults.aggregate.time}ms)`);
  console.log(`✓ Aggregate within 1s: ${testResults.aggregate.time < 1000 ? 'PASS' : 'FAIL'}`);
  
  if (testResults.aggregate.data) {
    console.log(`✓ Joined count: ${testResults.aggregate.data.joined_count}`);
    console.log(`✓ Enter event count: ${testResults.aggregate.data.enter_event_count}`);
    console.log(`✓ Version: ${testResults.aggregate.data.version}`);
  }
  
  const allPassed = 
    testResults.auth.success &&
    testResults.join.success &&
    testResults.event.success &&
    testResults.ack.received &&
    testResults.ack.time < 1000 &&
    testResults.aggregate.received &&
    testResults.aggregate.time < 1000;
  
  console.log(`\nOverall: ${allPassed ? '✓ PASS' : '✗ FAIL'}`);
  process.exit(allPassed ? 0 : 1);
}
