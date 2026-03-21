// ============================================================
// IoT Lab 2 - Electron Frontend JavaScript
// WiFi TCP client to Raspberry Pi
// ============================================================

const net = require("net");

let client = null;
let isConnected = false;
let pollTimer = null;
let recvBuffer = "";  // buffer for partial TCP data

function el(id) { return document.getElementById(id); }

// ---- Connection ----

function toggleConnection() {
  if (isConnected) { disconnect(); }
  else { connect(); }
}

function connect() {
  const ip = el("ipInput").value.trim();
  const port = parseInt(el("portInput").value.trim()) || 65432;

  if (!ip) { log("Enter Pi IP address!"); return; }

  log("Connecting to " + ip + ":" + port + "...");
  recvBuffer = "";

  client = new net.Socket();
  client.setTimeout(5000);

  client.connect(port, ip, () => {
    isConnected = true;
    log("Connected to Pi!");
    setConnUI(true);
    startPolling();
  });

  // Handle incoming data (may arrive in chunks)
  client.on("data", (data) => {
    recvBuffer += data.toString();
    // Process complete JSON lines
    let lines = recvBuffer.split("\n");
    // Keep the last (possibly incomplete) chunk in buffer
    recvBuffer = lines.pop();
    for (let line of lines) {
      line = line.trim();
      if (!line) continue;
      try {
        const status = JSON.parse(line);
        updateDisplay(status);
      } catch (e) {
        // not JSON, ignore
      }
    }
  });

  client.on("error", (err) => {
    log("Error: " + err.message);
    handleDisconnect();
  });

  client.on("close", () => {
    log("Connection closed.");
    handleDisconnect();
  });

  client.on("timeout", () => {
    log("Connection timed out.");
    client.destroy();
    handleDisconnect();
  });
}

function disconnect() {
  if (client) {
    try { client.write("stop\r\n"); } catch (e) {}
    client.destroy();
    client = null;
  }
  handleDisconnect();
  log("Disconnected.");
}

function handleDisconnect() {
  isConnected = false;
  stopPolling();
  setConnUI(false);
}

function setConnUI(on) {
  el("dot").className = on ? "dot green" : "dot red";
  el("connBtn").className = on ? "btn-conn off" : "btn-conn on";
  el("connBtn").innerText = on ? "Disconnect" : "Connect";
}

// ---- Send Commands ----

function sendCmd(cmd) {
  if (!isConnected || !client) { log("Not connected!"); return; }
  try {
    client.write(cmd + "\r\n");
    log("Sent: " + cmd);
  } catch (e) {
    log("Send error: " + e.message);
  }
}

function sendCustom() {
  const msg = el("msgInput").value.trim();
  if (!msg) return;
  sendCmd(msg);
  el("msgInput").value = "";
}

// ---- Polling (every 2 sec) ----

function startPolling() {
  stopPolling();
  pollTimer = setInterval(() => {
    if (isConnected && client) {
      try { client.write("GET_STATUS\r\n"); } catch (e) {}
    }
  }, 2000);
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
}

// ---- Update Status Display ----

function updateDisplay(s) {
  el("vTemp").innerText = (s.cpu_temp || 0) + " C";
  el("vBat").innerText = (s.battery_percent || 0) + "% (" + (s.battery_voltage || 0) + "V)";
  el("vSpd").innerText = s.speed || 0;
  el("vDir").innerText = s.direction || "--";
  el("vSteer").innerText = (s.steering_angle || 0) + " deg";
  el("vDist").innerText = (s.distance_traveled || 0) + " cm";
  el("vObst").innerText = (s.obstacle_dist || "???") + " cm";
  el("vTime").innerText = s.timestamp || "--:--:--";
}

// ---- Keyboard ----

document.addEventListener("keydown", (e) => {
  if (["ArrowUp","ArrowDown","ArrowLeft","ArrowRight"," "].includes(e.key)) {
    e.preventDefault();
  }
  switch (e.key) {
    case "ArrowUp": case "w": case "W": sendCmd("forward"); break;
    case "ArrowDown": case "s": case "S": sendCmd("backward"); break;
    case "ArrowLeft": case "a": case "A": sendCmd("left"); break;
    case "ArrowRight": case "d": case "D": sendCmd("right"); break;
    case " ": case "q": case "Q": sendCmd("stop"); break;
    case "Enter":
      if (document.activeElement === el("msgInput")) sendCustom();
      break;
  }
});

// ---- Log ----

function log(msg) {
  const t = new Date().toLocaleTimeString();
  el("logBar").innerText = "[" + t + "] " + msg;
}

// ---- Cleanup ----

window.addEventListener("beforeunload", () => {
  if (isConnected && client) {
    try { client.write("stop\r\n"); } catch (e) {}
    client.destroy();
  }
});
