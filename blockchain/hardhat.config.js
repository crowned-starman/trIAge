// blockchain/hardhat.config.js

require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config();

module.exports = {
  solidity: "0.8.24",
  networks: {
    monad_testnet: {
      url:      process.env.MONAD_RPC_URL || "https://testnet-rpc.monad.xyz",
      accounts: process.env.MONAD_PRIVATE_KEY
                  ? [process.env.MONAD_PRIVATE_KEY]
                  : [],
      chainId:  10143,
    },
    localhost: {
      url: "http://127.0.0.1:8545",
    },
  },
};
