// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

// 🧮 INTERFACES SOTA: Acoplamento atômico sem dependências externas (NPM)
interface IERC20 {
    function transfer(address recipient, uint256 amount) external returns (bool);
    function approve(address spender, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

interface ISwapRouter {
    struct ExactInputSingleParams {
        address tokenIn;
        address tokenOut;
        uint24 fee;
        address recipient;
        uint256 deadline;
        uint256 amountIn;
        uint256 amountOutMinimum;
        uint160 sqrtPriceLimitX96;
    }
    function exactInputSingle(ExactInputSingleParams calldata params) external payable returns (uint256 amountOut);
}

contract EpistemicQuantVault {
    address public immutable owner;
    address[] public validators;
    uint256 public constant THRESHOLD = 3; // 2/3 BFT Consensus
    
    ISwapRouter public immutable swapRouter;
    mapping(bytes32 => bool) public executedRoots;
    
    event BFTConsensusAchieved(bytes32 merkleRoot, uint256 validSignatures);
    event TradeExecuted(address indexed tokenIn, address indexed tokenOut, uint256 amountIn, uint256 amountOut);
    event AlphaExtracted(address indexed token, uint256 amount);

    constructor(address[] memory _validators, address _swapRouter) {
        owner = msg.sender;
        validators = _validators;
        swapRouter = ISwapRouter(_swapRouter);
    }

    function recoverSigner(bytes32 messageHash, bytes memory signature) internal pure returns (address) {
        require(signature.length == 65, "Invalid signature length");
        bytes32 r; bytes32 s; uint8 v;
        assembly {
            r := mload(add(signature, 32))
            s := mload(add(signature, 64))
            v := byte(0, mload(add(signature, 96)))
        }
        bytes32 ethSignedMessageHash = keccak256(abi.encodePacked("\x19Ethereum Signed Message:\n32", messageHash));
        return ecrecover(ethSignedMessageHash, v, r, s);
    }

    // 🧮 A INVARIANTE DA LIQUIDAÇÃO: Valida consenso P2P e executa a ordem DEX.
    function batchSettleAndSwap(
        bytes32 merkleRoot,
        bytes[] calldata signatures,
        address tokenIn,
        address tokenOut,
        uint24 poolFee,
        uint256 amountIn,
        uint256 amountOutMinimum
    ) external {
        require(!executedRoots[merkleRoot], "Root already executed");
        require(signatures.length >= THRESHOLD, "Insufficient BFT signatures");

        uint256 validSigs = 0;
        address[] memory recovered = new address[](signatures.length);

        for (uint i = 0; i < signatures.length; i++) {
            address signer = recoverSigner(merkleRoot, signatures[i]);
            
            bool isValidator = false;
            for (uint j = 0; j < validators.length; j++) {
                if (signer == validators[j]) { isValidator = true; break; }
            }
            require(isValidator, "Sybil detected");
            
            bool isDuplicate = false;
            for (uint k = 0; k < validSigs; k++) {
                if (recovered[k] == signer) { isDuplicate = true; break; }
            }
            require(!isDuplicate, "Duplicate signature");
            
            recovered[validSigs] = signer;
            validSigs++;
        }

        require(validSigs >= THRESHOLD, "BFT Threshold failed");
        executedRoots[merkleRoot] = true;
        emit BFTConsensusAchieved(merkleRoot, validSigs);

        // 🧮 ROTEAMENTO DE LIQUIDEZ (Uniswap V3)
        // O contrato autoriza o roteador a gastar seu saldo e executa a troca.
        IERC20(tokenIn).approve(address(swapRouter), amountIn);
        
        ISwapRouter.ExactInputSingleParams memory params = ISwapRouter.ExactInputSingleParams({
            tokenIn: tokenIn,
            tokenOut: tokenOut,
            fee: poolFee,
            recipient: address(this), // O capital resultante volta para o próprio cofre
            deadline: block.timestamp + 15,
            amountIn: amountIn,
            amountOutMinimum: amountOutMinimum,
            sqrtPriceLimitX96: 0
        });

        uint256 amountOut = swapRouter.exactInputSingle(params);
        emit TradeExecuted(tokenIn, tokenOut, amountIn, amountOut);
    }

    // 🧮 A INVARIANTE DA EXTRAÇÃO: Acesso estrito ao lucro.
    function extractAlpha(address token, uint256 amount) external {
        require(msg.sender == owner, "Only Owner");
        require(IERC20(token).transfer(owner, amount), "Transfer failed");
        emit AlphaExtracted(token, amount);
    }
}
