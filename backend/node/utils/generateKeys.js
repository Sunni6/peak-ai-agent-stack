const crypto = require('crypto');

// Generate API key
const generateApiKey = () => {
    return crypto.randomBytes(32).toString('hex');
};

// Generate JWT Secret
const generateJwtSecret = () => {
    return crypto.randomBytes(64).toString('base64');
};

// Get client number from command line argument
const clientNumber = process.argv[2];

if (!clientNumber) {
    console.error('Please provide a client number: node generateKeys.js <clientNumber>');
    process.exit(1);
}

console.log(`\nGenerated keys for Client ${clientNumber}:`);
console.log('----------------------------------------');
console.log(`${clientNumber}_API_KEY=${generateApiKey()}`);
console.log(`${clientNumber}_SECRET=${generateJwtSecret()}`);
