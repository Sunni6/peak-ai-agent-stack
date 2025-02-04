const Redis = require('ioredis');
const config = require('../config');

// Module-level variable to hold the Redis client instance
let redisClient = null;

// Function to initialize the Redis connection
const connectToRedis = async () => {
    try {
        // Only create a new client if one doesn't exist
        if (!redisClient) {
            console.log('Redis Configuration:', {
                host: config.redis.host,
                port: config.redis.port,
                tls: false  // Explicitly set TLS to false
            });

            redisClient = new Redis({
                ...config.redis,
                tls: false,  // Explicitly disable TLS
                retryStrategy(times) {
                    if (times > 5) {
                        console.error('❌ Redis retry limit exceeded');
                        return null; // stop retrying
                    }
                    const delay = Math.min(times * 50, 2000);
                    console.log(`Retrying Redis connection in ${delay}ms...`);
                    return delay;
                }
            });

            // Set up event listeners
            redisClient.on('error', (err) => {
                console.error('❌ Redis Client Error:', err.message);
            });

            redisClient.on('connect', () => {
                console.log('✅ Connected to Redis Cloud successfully');
            });

            // Test the connection
            await redisClient.ping();
        }
        
        return redisClient;
    } catch (error) {
        console.error('❌ Failed to connect to Redis:', error.message);
        throw error;
    }
};

// Helper function for multiple HSET operations
const hsetMultiple = async (key, fields) => {
    if (!redisClient) {
        throw new Error('Redis client not initialized');
    }
    const multi = redisClient.multi();
    Object.entries(fields).forEach(([field, value]) => {
        multi.hset(key, field, value);
    });
    return multi.exec();
};

// Get the Redis client instance
const client = () => {
    if (!redisClient) {
        throw new Error('Redis client not initialized');
    }
    return redisClient;
};

// Graceful shutdown handler
const closeRedisConnection = async () => {
    if (redisClient) {
        console.log('Closing Redis connection...');
        await redisClient.quit();
        redisClient = null;
    }
};

module.exports = {
    connectToRedis,
    closeRedisConnection,
    hsetMultiple,
    client
};
