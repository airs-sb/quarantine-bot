const mineflayer = require('mineflayer');
const { SocksClient } = require('socks');
const axios = require('axios');

let bot;
let isBanned = false;

// Define Values
const ssid = process.argv[2];  
const uuid = process.argv[3]; 
const username = process.argv[4]; 
const webhook = process.argv[5]; 
const proxyHost = process.argv[6]; 
const proxyPort = process.argv[7]; 
const proxyUsername = process.argv[8]; 
const proxyPassword = process.argv[9]; 
const time = process.argv[10];
const ticksinsec = parseInt(time) * 60 * 1000;

console.log(`Bot will shut down after ${time} minutes.`);
console.log(`Bot will connect to hypixel.net:25565 via proxy.`);
console.log(`Proxy: ${proxyHost}:${proxyPort}`);

process.on('SIGTERM', () => {
  console.log('Received termination signal. Terminating...');
  process.exit(0);
});

// Setup Mineflayer
const botOptions = {
  host: 'mc.hypixel.net',  
  port: 25565,
  version: '1.8.9',
  username: username,
  session: {
    accessToken: ssid,
    clientToken: uuid,
    selectedProfile: {
      id: uuid,
      name: username,
    },
  },
  auth: 'mojang',
  skipValidation: true,
  connect: (client) => {
    const options = {
      proxy: {
        host: proxyHost,
        port: parseInt(proxyPort),
        type: 5,
        userId: proxyUsername,
        password: proxyPassword
      },
      destination: {
        host: 'mc.hypixel.net',
        port: 25565
      },
      command: 'connect'
    };

    SocksClient.createConnection(options, (err, info) => {
      if (err) {
        console.error('Error creating SOCKS connection:', err);
        return;
      }
      console.log('Connected through proxy.');
      client.setSocket(info.socket);
      client.emit('connect');
    });
  }
};

// Create Mineflayer Bot
function createBot() {
  bot = mineflayer.createBot(botOptions);
  
  bot.once('spawn', () => {
    console.log(`Bot logged into Hypixel as ${username}`);
  });

  bot.on('end', () => {
    console.log('Connection lost');
    if (!isBanned) { 
      setTimeout(reconnect, getRandomDelay());
    } else {
      console.log('Bot is banned, exiting...');
      axios.post(webhook, {
        username: 'Reaper',
        content: `${username} Account is banned.`
      });
      process.exit();
    }
  });

  bot.on('kicked', (reason) => {
    console.log('Kicked for reason:', reason);
    let isBanned = false;
    let banReason = '';
    
    try {
      const reasonObj = JSON.parse(reason);
      if (reasonObj.extra && Array.isArray(reasonObj.extra)) {
        const extra = reasonObj.extra;
        const banMessage = extra.find(item => item.text && item.text.toLowerCase().includes("banned"));
        if (banMessage) {
          isBanned = true;
          banReason = extra.map(item => item.text).join('');
        }
      }
    } catch (error) {
      console.error('Error parsing kick reason:', error);
    }
    
    if (isBanned) {
      console.log('Account is banned. Reason:', banReason);
      axios.post(webhook, {
        username: 'Astral Quarantine',
        content: `${username} Account is banned. Reason: ${banReason}`,
      })
      .then(() => process.exit())
      .catch((error) => {
        console.error('Error sending webhook:', error);
        process.exit();
      });
    } else {
      axios.post(webhook, {
        username: 'Auto-kick',
        content: `**:no_entry: Victim join detected** -> Rejoining Hypixel :white_check_mark: Account | ${username}`,
      })
      .catch((error) => console.error('Error sending webhook:', error));
      setTimeout(reconnect, getRandomDelay());
    }
  });

  bot.on('message', (message) => {
    console.log(`Message from server: ${message}`);
  });

  bot.on('error', (error) => {
    console.error('Bot error:', error);
  });
}

function reconnect() {
  if (!isBanned) {
    createBot();
  }
}

function getRandomDelay() {
  return Math.floor(Math.random() * 10000) + 5000;
}

setTimeout(() => {
  console.log("Time's up! Closing the window...");
  process.exit();
}, ticksinsec);

createBot();
