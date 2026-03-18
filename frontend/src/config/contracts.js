// src/config/contracts.js

export const TOKEN_ADDRESS = "0xD46FD6d0f0A6360fA3E6fdF4C026eCE8eD1711FA";
export const VAULT_ADDRESS = "0xbC54b65B87Dd9E47549c29056eBde38fBa47ba10";

export const ERC20_ABI = [
    "function approve(address spender, uint256 amount) public returns (bool)",
    "function allowance(address owner, address spender) public view returns (uint256)",
    "function balanceOf(address account) public view returns (uint256)"
];

export const VAULT_ABI = [
    "function deposit(uint256 amount) external",
    "function withdraw(uint256 amount, uint256 nonce, bytes memory signature) external",
    "event Deposit(address indexed user, uint256 amount)",
    "event Withdraw(address indexed user, uint256 amount, uint256 timestamp)"
];