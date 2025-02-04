const jwt = require('jsonwebtoken');
const config = require('../config');

const validApiKeys = Object.entries(config.auth.clients).reduce((acc, [clientId, clientConfig]) => {
    return { ...acc, [clientConfig.apiKey]: clientId };
}, {});

const generateToken = (apiKey) => {
    const clientId = validApiKeys[apiKey];
    if (!clientId) {
        throw new Error('Invalid API key');
    }
    const clientConfig = config.auth.clients[clientId];
    
    // Generate access token
    const accessToken = jwt.sign(
        { 
            clientId, 
            type: 'access',
            scopes: clientConfig.scopes 
        },
        clientConfig.secret,
        {
            expiresIn: clientConfig.accessTokenExpiry,
            algorithm: config.auth.accessToken.algorithm,
            issuer: config.auth.accessToken.issuer,
            audience: config.auth.accessToken.audience
        }
    );

    // Generate refresh token
    const refreshToken = jwt.sign(
        { 
            clientId,
            type: 'refresh'
        },
        clientConfig.secret,
        {
            expiresIn: clientConfig.refreshTokenExpiry,
            algorithm: config.auth.refreshToken.algorithm
        }
    );

    return {
        accessToken,
        refreshToken,
        expiresIn: clientConfig.accessTokenExpiry
    };
};

const verifyToken = (token, expectedType = 'access') => {
    try {
        // First decode without verification to get clientId
        const decoded = jwt.decode(token);
        if (!decoded || !decoded.clientId) {
            console.log('Token decode failed:', decoded);
            return null;
        }

        // Get client config
        const clientConfig = config.auth.clients[decoded.clientId];
        if (!clientConfig) {
            console.log('Client config not found for:', decoded.clientId);
            return null;
        }

        // Verify token with client's secret
        const verified = jwt.verify(token, clientConfig.secret, {
            algorithms: [expectedType === 'access' ? 
                config.auth.accessToken.algorithm : 
                config.auth.refreshToken.algorithm
            ],
            ...(expectedType === 'access' ? {
                issuer: config.auth.accessToken.issuer,
                audience: config.auth.accessToken.audience
            } : {})
        });

        // Verify token type
        if (verified.type !== expectedType) {
            console.log('Token type mismatch:', verified.type, 'expected:', expectedType);
            return null;
        }

        return verified;
    } catch (error) {
        console.log('Token verification error:', error.message);
        return null;
    }
};

const refreshTokens = (refreshToken) => {
    const verified = verifyToken(refreshToken, 'refresh');
    if (!verified) {
        throw new Error('Invalid refresh token');
    }

    // Get client config and generate new tokens
    const clientConfig = config.auth.clients[verified.clientId];
    return generateToken(clientConfig.apiKey);
};

module.exports = { generateToken, verifyToken, refreshTokens };
