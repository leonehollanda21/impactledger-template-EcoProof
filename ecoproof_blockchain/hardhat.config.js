require("@nomicfoundation/hardhat-toolbox");
require("@openzeppelin/hardhat-upgrades");
require("dotenv").config();

// Valores-padrão seguros para CI ou inicialização
const MINTER_PRIVATE_KEY = process.env.MINTER_PRIVATE_KEY || "0x" + "0".repeat(64);
const WEB3_PROVIDER_URL  = process.env.WEB3_PROVIDER_URL  || "https://rpc.sepolia.org";
const ETHERSCAN_API_KEY  = process.env.ETHERSCAN_API_KEY  || "";
const POLYGONSCAN_API_KEY = process.env.POLYGONSCAN_API_KEY || "";

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: {
    version: "0.8.24",
    settings: {
      evmVersion: "cancun",
      optimizer: {
        enabled: true,
        runs: 200, 
      },
      viaIR: true,
    },
  },

  networks: {
    // ─── Rede local (hardhat node) ────────────────────────────────
    localhost: {
      url: "http://127.0.0.1:8545",
    },

    // ─── Ethereum Sepolia (testnet) ───────────────────────────────
    sepolia: {
      url: WEB3_PROVIDER_URL,
      accounts: [MINTER_PRIVATE_KEY],
      chainId: 11155111,
    },

    // ─── Polygon Amoy (testnet atual — substitui Mumbai) ─────────
    amoy: {
      url: process.env.POLYGON_AMOY_URL || "https://rpc-amoy.polygon.technology",
      accounts: [MINTER_PRIVATE_KEY],
      chainId: 80002,
      gasPrice: 30000000000, // 30 gwei
    },

    // ─── Polygon PoS Mainnet ─────────────────────────────────────
    polygon: {
      url: process.env.POLYGON_MAINNET_URL || "https://polygon-rpc.com",
      accounts: [MINTER_PRIVATE_KEY],
      chainId: 137,
    },

    // ─── Ethereum Mainnet ─────────────────────────────────────────
    mainnet: {
      url: process.env.ETH_MAINNET_URL || "https://eth.llamarpc.com",
      accounts: [MINTER_PRIVATE_KEY],
      chainId: 1,
    },
  },

  // Verificação automática após deploy
  etherscan: {
    apiKey: {
      sepolia: ETHERSCAN_API_KEY,
      mainnet: ETHERSCAN_API_KEY,
      polygon: POLYGONSCAN_API_KEY,
      polygonAmoy: POLYGONSCAN_API_KEY,
    },
    customChains: [
      {
        network: "polygonAmoy",
        chainId: 80002,
        urls: {
          apiURL: "https://api-amoy.polygonscan.com/api",
          browserURL: "https://amoy.polygonscan.com",
        },
      },
    ],
  },

  // Relatório de gas em testes
  gasReporter: {
    enabled: process.env.REPORT_GAS === "true",
    currency: "USD",
    token: "MATIC",
  },

  // Cobertura de testes
  coverage: {
    exclude: ["test/", "scripts/"],
  },
};