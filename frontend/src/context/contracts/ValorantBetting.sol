// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

contract ValorantBetting is Ownable, ReentrancyGuard {
    
    enum Team { NONE, WIN, LOSS } // WIN = Blue/Own, LOSS = Red/Enemy
    
    struct Round {
        bool isResolved;
        Team winner;
        uint256 totalWinBets;
        uint256 totalLossBets;
        mapping(address => uint256) winBets;
        mapping(address => uint256) lossBets;
    }

    mapping(string => mapping(string => Round)) public rounds;

    event BetPlaced(string lobbyId, string roundId, address user, Team team, uint256 amount);
    event RoundResolved(string lobbyId, string roundId, Team winner, uint256 totalPool);
    event WinningsClaimed(string lobbyId, string roundId, address user, uint256 amount);

    constructor() Ownable(msg.sender) {}

    // View function for UI Prediction Bar
    function getRoundStats(string calldata lobbyId, string calldata roundId) external view returns (uint256, uint256) {
        Round storage r = rounds[lobbyId][roundId];
        return (r.totalWinBets, r.totalLossBets);
    }

    function placeBet(string calldata lobbyId, string calldata roundId, Team team) external payable nonReentrant {
        require(msg.value > 0, "Bet must be > 0");
        require(team != Team.NONE, "Invalid team");
        
        Round storage r = rounds[lobbyId][roundId];
        require(!r.isResolved, "Round ended");

        if (team == Team.WIN) {
            r.winBets[msg.sender] += msg.value;
            r.totalWinBets += msg.value;
        } else {
            r.lossBets[msg.sender] += msg.value;
            r.totalLossBets += msg.value;
        }
        emit BetPlaced(lobbyId, roundId, msg.sender, team, msg.value);
    }

    function resolveRound(string calldata lobbyId, string calldata roundId, Team winner) external onlyOwner {
        Round storage r = rounds[lobbyId][roundId];
        require(!r.isResolved, "Already resolved");
        
        r.isResolved = true;
        r.winner = winner;

        emit RoundResolved(lobbyId, roundId, winner, r.totalWinBets + r.totalLossBets);
    }

    function claimWinnings(string calldata lobbyId, string calldata roundId) external nonReentrant {
        Round storage r = rounds[lobbyId][roundId];
        require(r.isResolved, "Round not resolved");

        uint256 payout = 0;
        uint256 userBet = 0;
        uint256 winningPool = 0;
        uint256 losingPool = 0;

        if (r.winner == Team.WIN) {
            userBet = r.winBets[msg.sender];
            winningPool = r.totalWinBets;
            losingPool = r.totalLossBets;
            r.winBets[msg.sender] = 0; 
        } else if (r.winner == Team.LOSS) {
            userBet = r.lossBets[msg.sender];
            winningPool = r.totalLossBets;
            losingPool = r.totalWinBets;
            r.lossBets[msg.sender] = 0;
        } else {
            // Draw/Refund logic
            userBet = r.winBets[msg.sender] + r.lossBets[msg.sender];
            r.winBets[msg.sender] = 0;
            r.lossBets[msg.sender] = 0;
            
            (bool s, ) = payable(msg.sender).call{value: userBet}("");
            require(s, "Refund failed");
            return;
        }

        require(userBet > 0, "No winnings/bets found");

        if (losingPool == 0) {
            payout = userBet; 
        } else {
            uint256 profit = (userBet * losingPool) / winningPool;
            payout = userBet + profit;
        }

        (bool success, ) = payable(msg.sender).call{value: payout}("");
        require(success, "Payout failed");

        emit WinningsClaimed(lobbyId, roundId, msg.sender, payout);
    }
}