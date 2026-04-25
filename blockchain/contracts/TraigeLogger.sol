// blockchain/contracts/TriageLogger.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract TriageLogger {

    // Events
    event TriageEventLogged(
        bytes32 indexed eventHash,
        address indexed logger,
        uint256 timestamp
    );

    // State
    address public owner;
    uint256 public totalEvents;

    mapping(bytes32 => uint256) public eventTimestamps;  // hash → timestamp
    mapping(bytes32 => bool)    public eventExists;      // dedup check

    // Modifiers
    modifier onlyOwner() {
        require(msg.sender == owner, "Not authorized");
        _;
    }

    // Constructor
    constructor() {
        owner = msg.sender;
    }

    // Functions

    /**
     * @notice Log a triage event hash on-chain.
     * @dev    No medical data is stored — only the SHA-256 hash.
     * @param  eventHash SHA-256 hash of the off-chain triage event.
     */
    function logEvent(bytes32 eventHash) external onlyOwner {
        require(!eventExists[eventHash], "Event already logged");

        eventExists[eventHash]     = true;
        eventTimestamps[eventHash] = block.timestamp;
        totalEvents               += 1;

        emit TriageEventLogged(eventHash, msg.sender, block.timestamp);
    }

    /**
     * @notice Verify whether a hash was logged on-chain.
     * @param  eventHash Hash to verify.
     * @return exists    True if the hash was logged.
     * @return timestamp Block timestamp when it was logged (0 if not found).
     */
    function verifyEvent(bytes32 eventHash)
        external
        view
        returns (bool exists, uint256 timestamp)
    {
        return (eventExists[eventHash], eventTimestamps[eventHash]);
    }
}
