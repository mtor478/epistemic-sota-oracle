// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

contract EpistemicClearingHouse {
    address public immutable oracle;
    
    // EIP-712 Domain Separator
    bytes32 public immutable DOMAIN_SEPARATOR;
    bytes32 public constant PAYMENT_TYPEHASH = keccak256("Payment(address agent,uint256 amount,uint256 nonce)");

    mapping(address => uint256) public nonces;
    mapping(address => uint256) public escrows;

    constructor() {
        oracle = msg.sender;
        DOMAIN_SEPARATOR = keccak256(
            abi.encode(
                keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
                keccak256(bytes("EpistemicOracle")),
                keccak256(bytes("1")),
                block.chainid,
                address(this)
            )
        );
    }

    // Agente tranca o capital com antecedência (Fora do caminho crítico)
    function depositEscrow() external payable {
        escrows[msg.sender] += msg.value;
    }

    // 🧮 A INVARIANTE MEV: Liquidação assíncrona O(1) pelo Oráculo
    function cashOutChannel(address agent, uint256 amount, uint256 nonce, uint8 v, bytes32 r, bytes32 s) external {
        require(msg.sender == oracle, "Only Oracle");
        require(nonce > nonces[agent], "Invalid nonce / Replay Attack");
        require(escrows[agent] >= amount, "Insufficient Escrow");

        bytes32 structHash = keccak256(abi.encode(PAYMENT_TYPEHASH, agent, amount, nonce));
        bytes32 digest = keccak256(abi.encodePacked("\x19\x01", DOMAIN_SEPARATOR, structHash));
        
        address signer = ecrecover(digest, v, r, s);
        require(signer == agent, "Invalid ECDSA Signature");

        nonces[agent] = nonce;       // Fecha a janela de Replay Attack
        escrows[agent] -= amount;    // Deduz do saldo
        
        payable(oracle).transfer(amount); // Liquidação termodinâmica final
    }
}
