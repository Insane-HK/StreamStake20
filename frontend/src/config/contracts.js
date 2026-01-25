// src/config/contracts.js

export const TOKEN_ADDRESS = "0xd9145CCE52D386f254917e481eB44e9943F39138";
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