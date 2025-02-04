const mongoose = require('mongoose');
const config = require('../config');

let connection;

const connectToMongoDB = async () => {
    try {
        console.log('🔌 Connecting to MongoDB...');
        console.log('MONGO_URI:', config.mongoUri ? '[REDACTED]' : 'Not set');

        if (!config.mongoUri) {
            throw new Error('MongoDB URI is not configured');
        }

        if (connection && mongoose.connection.readyState === 1) {
            return connection;
        }

        connection = await mongoose.connect(config.mongoUri, {
            useNewUrlParser: true,
            useUnifiedTopology: true
        });

        console.log('Connected to MongoDB');
        return connection;
    } catch (error) {
        console.error('Failed to connect to MongoDB:', error);
        throw error;
    }
};

const ensureConnection = async () => {
    if (!connection || mongoose.connection.readyState !== 1) {
        return await connectToMongoDB();
    }
    return connection;
};

module.exports = {
    connection: () => connection,
    connectToMongoDB,
    ensureConnection
};
