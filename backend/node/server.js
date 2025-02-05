/**
 * Copyright (c) 2025 dleerdefi & Aggregated AI
 * Licensed under the MIT License. See LICENSE in the project root for license information.
 */

require('dotenv').config();
const express = require('express');
const mongoose = require('mongoose');
const config = require('./config');
const { connectToMongoDB } = require('./utils/mongoClient');
const morgan = require('morgan');
const logger = require('./utils/logger');
const { spawn } = require('child_process');
const path = require('path');
const axios = require('axios');
const cors = require('cors');
const rinRoutes = require('./routes/rinRoutes');

const app = express();
const frontendApp = express();

// Backend port (3000) - for Python service, MongoDB, etc.
const BACKEND_PORT = process.env.BACKEND_PORT || 3000;

// Frontend port (3003) - for serving the client
const FRONTEND_PORT = process.env.FRONTEND_PORT || 3003;

app.set('trust proxy', 1);

// Backend server configuration
app.use(cors({
    origin: ['http://localhost:3003'],
    credentials: true
}));
app.use(express.json());
app.use('/api/rin', rinRoutes);  // Only Rin routes
app.use(morgan('combined', { stream: logger.stream }));

// Health check endpoint
app.get('/health', (req, res) => {
    res.json({ status: 'OK', message: 'Backend operational' });
});

// Add a catch-all route to serve index.html for all non-API routes
app.get('*', (req, res) => {
    if (!req.path.startsWith('/api')) {
        logger.info('Serving index.html');
        res.sendFile(path.join(__dirname, '../../frontend/index.html'));
    }
});

// Health check endpoint
app.get('/api/health', (req, res) => {
    res.json({ status: 'OK', message: 'Services operational' });
});

// Error handling middleware
app.use((err, req, res, next) => {
    logger.error(err.stack);
    res.status(500).json({ 
        status: 'error', 
        message: 'Internal server error' 
    });
});

// Log all uncaught exceptions
process.on('uncaughtException', (error) => {
    logger.error('Uncaught Exception:', error);
    process.exit(1);
});

// Log all unhandled promise rejections
process.on('unhandledRejection', (error) => {
    logger.error('Unhandled Rejection:', error);
});

// Initialize Python API server
async function startPythonServer() {
    return new Promise((resolve, reject) => {
        logger.info('Starting Python service...');
        
        // Get the path to the Python services directory
        const pythonPath = path.join(__dirname, '../python_services');
        const venvPython = process.platform === 'win32' 
            ? path.join(pythonPath, 'venv', 'Scripts', 'python.exe')
            : path.join(pythonPath, 'venv', 'bin', 'python');

        // Spawn Python process
        const pythonProcess = spawn(venvPython, [
            '-m', 'uvicorn',
            'api_server:app',
            '--host', '0.0.0.0',
            '--port', '8000'
        ], {
            cwd: pythonPath,
            env: { ...process.env }
        });

        // Handle Python process output
        pythonProcess.stdout.on('data', (data) => {
            logger.info(`Python service: ${data}`);
        });

        pythonProcess.stderr.on('data', (data) => {
            logger.error(`Python service error: ${data}`);
        });

        // Check if service is ready
        const checkService = async () => {
            try {
                const response = await fetch('http://localhost:8000/health');
                if (response.ok) {
                    logger.info('✅ Python service is ready');
                    resolve(pythonProcess);
                } else {
                    setTimeout(checkService, 1000);
                }
            } catch (error) {
                if (error.code === 'ECONNREFUSED') {
                    setTimeout(checkService, 1000);
                } else {
                    reject(error);
                }
            }
        };

        // Give Python service more time to start
        setTimeout(checkService, 10000);

        // Handle process errors
        pythonProcess.on('error', (error) => {
            logger.error('Failed to start Python service:', error);
            reject(error);
        });

        pythonProcess.on('close', (code) => {
            if (code !== 0) {
                logger.error(`Python service exited with code ${code}`);
                reject(new Error(`Python service exited with code ${code}`));
            }
        });
    });
}

// Frontend server configuration
frontendApp.use(cors());
frontendApp.use(express.json());

// Add request logging for debugging
frontendApp.use((req, res, next) => {
    logger.info(`[${req.method}] ${req.path}`);
    next();
});

// Proxy all API requests to backend
frontendApp.use('/api', (req, res, next) => {
    const backendPath = `/api${req.url}`;
    logger.info(`Proxying request to backend: ${req.method} ${backendPath}`);
    
    // Forward all headers including Authorization
    const headers = {
        ...req.headers,
        host: `localhost:${BACKEND_PORT}`,
        'Content-Type': 'application/json'
    };

    axios({
        method: req.method,
        url: `http://localhost:${BACKEND_PORT}${backendPath}`,
        data: req.body,
        headers: headers
    })
    .then(response => {
        logger.info(`Proxy response status: ${response.status}`);
        res.status(response.status).json(response.data);
    })
    .catch(error => {
        logger.error('Proxy error:', error.message);
        logger.error('Error details:', {
            status: error.response?.status,
            data: error.response?.data,
            path: backendPath,
            originalUrl: req.originalUrl,
            headers: headers  // Log headers for debugging
        });
        res.status(error.response?.status || 500).json(
            error.response?.data || { error: 'Proxy error' }
        );
    });
});

// Frontend static files (after API routes)
frontendApp.use('/public', express.static(path.join(__dirname, '../../frontend/public')));
frontendApp.use(express.static(path.join(__dirname, '../../frontend')));

// Frontend catch-all route (must be last)
frontendApp.get('*', (req, res) => {
    if (!req.path.startsWith('/api')) {
        res.sendFile(path.join(__dirname, '../../frontend/index.html'));
    }
});

// Initialize services and start servers
const startServer = async () => {
    try {
        // Initialize core services
        await connectToMongoDB();
        logger.info('✅ MongoDB connected successfully');

        // Start Python API server
        const pythonProcess = await startPythonServer();
        logger.info('✅ Python service started successfully');

        // Start both servers
        app.listen(BACKEND_PORT, () => {
            logger.info(`✅ Backend server running on port ${BACKEND_PORT}`);
        });

        frontendApp.listen(FRONTEND_PORT, () => {
            logger.info(`✅ Frontend server running on port ${FRONTEND_PORT}`);
        });

        // Cleanup handler
        process.on('SIGTERM', async () => {
            logger.info('Shutting down...');
            if (pythonProcess) pythonProcess.kill();
            await mongoose.connection.close();
            process.exit(0);
        });

    } catch (error) {
        logger.error("❌ Failed to start server:", error);
        process.exit(1);
    }
};

// Start the servers
startServer();

module.exports = { app, frontendApp };