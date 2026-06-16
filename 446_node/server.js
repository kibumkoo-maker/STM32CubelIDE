/**
 * HC-SR04 듀얼 채널 실시간 거리 모니터 서버
 *
 * STM32 출력 형식:
 *   Distance1 = 608(mm)
 *   Distance2 = 423(mm)
 *   Out of Range!
 *
 * 실행: node server.js [포트] [시리얼포트]
 *   node server.js 3000 demo         ← 시뮬레이션
 *   node server.js 3000 COM3         ← Windows
 *   node server.js 3000 /dev/ttyACM0 ← Linux
 */

const express = require('express');
const http    = require('http');
const { Server } = require('socket.io');
const path    = require('path');

const app    = express();
const server = http.createServer(app);
const io     = new Server(server);

const PORT        = process.argv[2] || 3000;
const SERIAL_PORT = process.argv[3] || 'demo';

app.use(express.static(path.join(__dirname, 'public')));

// ──────────────────────────────────────────────────
// 파서: "Distance1 = 608(mm)" / "Distance2 = 423(mm)"
// 반환: { ch: 1|2, value: number|null, outOfRange: bool }
// ──────────────────────────────────────────────────
function parseLine(line) {
  const m = line.match(/Distance([12])\s*=\s*(\d+)\s*\(mm\)/i);
  if (m) return { ch: parseInt(m[1]), value: parseInt(m[2]), outOfRange: false };
  if (/out of range/i.test(line)) return { ch: 0, value: null, outOfRange: true };
  return null;
}

// ──────────────────────────────────────────────────
// 시리얼 포트
// ──────────────────────────────────────────────────
function startSerial(portName) {
  try {
    const { SerialPort }     = require('serialport');
    const { ReadlineParser } = require('@serialport/parser-readline');

    const port   = new SerialPort({ path: portName, baudRate: 115200 });
    const parser = port.pipe(new ReadlineParser({ delimiter: '\r\n' }));

    parser.on('data', (line) => {
      const data = parseLine(line.trim());
      if (data) io.emit('distance', { ...data, ts: Date.now() });
    });

    port.on('open',  () => console.log(`✅ Serial open: ${portName}`));
    port.on('error', (e) => console.error('Serial error:', e.message));

  } catch (e) {
    console.warn('⚠️  serialport 모듈 없음 → demo 모드로 전환');
    startDemo();
  }
}

// ──────────────────────────────────────────────────
// Demo 시뮬레이션 — CH1, CH2 독립 랜덤워크
// ──────────────────────────────────────────────────
function startDemo() {
  let base1 = 500, base2 = 1200;

  setInterval(() => {
    base1 += (Math.random() - 0.48) * 35;
    base1 = Math.max(50, Math.min(4000, base1));
    const oor1 = Math.random() < 0.03;
    io.emit('distance', { ch: 1, value: oor1 ? null : Math.round(base1), outOfRange: oor1, ts: Date.now() });
  }, 200);

  setInterval(() => {
    base2 += (Math.random() - 0.47) * 50;
    base2 = Math.max(50, Math.min(4000, base2));
    const oor2 = Math.random() < 0.03;
    io.emit('distance', { ch: 2, value: oor2 ? null : Math.round(base2), outOfRange: oor2, ts: Date.now() });
  }, 200);

  console.log('🟡 Demo 시뮬레이션 실행 중 (CH1 + CH2)...');
}

// ──────────────────────────────────────────────────
// Socket
// ──────────────────────────────────────────────────
io.on('connection', (socket) => {
  console.log(`🔌 Client connected: ${socket.id}`);
  socket.on('disconnect', () => console.log(`❌ Client disconnected: ${socket.id}`));
  socket.on('inject', (line) => {
    const data = parseLine(line);
    if (data) io.emit('distance', { ...data, ts: Date.now() });
  });
});

// ──────────────────────────────────────────────────
// 시작
// ──────────────────────────────────────────────────
if (SERIAL_PORT === 'demo') startDemo();
else startSerial(SERIAL_PORT);

server.listen(PORT, () => {
  console.log(`🚀 서버 실행: http://localhost:${PORT}`);
  console.log(`   포트 모드: ${SERIAL_PORT}`);
});
