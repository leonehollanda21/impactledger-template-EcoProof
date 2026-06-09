// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts-upgradeable/token/ERC721/extensions/ERC721URIStorageUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/access/AccessControlUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/utils/PausableUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/Initializable.sol";
import "@openzeppelin/contracts/utils/cryptography/MerkleProof.sol";

// ── Custom Errors ────────────────────────────────────────────────────────────
error SoulboundNaoTransferivel();
error ReentrantCall();
error AlreadyMinted(bytes32 offchainId);
error AlreadyClaimed(uint256 eventoId, address cidadao);
error InvalidMerkleProof();
error MerkleRootNotSet(uint256 eventoId);
error InvalidBatchSize();
error EmptyBatch();

// ── EIP-5192: Minimal Soulbound Interface ────────────────────────────────────
interface IERC5192 {
    event Locked(uint256 tokenId);
    event Unlocked(uint256 tokenId);
    function locked(uint256 tokenId) external view returns (bool);
}

/**
 * @title InstitutoNFT (ECOE — EcoProof Evento)
 * @notice Soulbound Token (SBT) para eventos de mutirão organizados por institutos.
 * @dev Implementa EIP-5192 + Merkle Tree para mint em lote eficiente.
 *
 *      Dois modos de mint:
 *      1. mintEvento() — Backend minta diretamente (MINTER_ROLE)
 *      2. setMerkleRoot() + claimNFT() — Instituto registra root, cidadão reclama com proof
 *
 *      Cada token armazena o endereço do instituto on-chain.
 *      Peso: 30 pontos por participação em mutirão.
 */
contract InstitutoNFT is
    Initializable,
    ERC721URIStorageUpgradeable,
    AccessControlUpgradeable,
    PausableUpgradeable,
    UUPSUpgradeable,
    IERC5192
{
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant INSTITUTE_ROLE = keccak256("INSTITUTE_ROLE");
    bytes32 public constant UPGRADER_ROLE = keccak256("UPGRADER_ROLE");
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");

    // Proxy-safe reentrancy guard (no constructor)
    uint256 private constant _NOT_ENTERED = 1;
    uint256 private constant _ENTERED = 2;
    uint256 private _reentrancyStatus;

    modifier nonReentrant() {
        if (_reentrancyStatus == _ENTERED) revert ReentrantCall();
        _reentrancyStatus = _ENTERED;
        _;
        _reentrancyStatus = _NOT_ENTERED;
    }

    enum ActionType { LIXO_RUA, PRAIA, CORREGO, QUEIMADA, OUTRO }

    struct EventoNFTRecord {
        address citizen;
        address institutionWallet;
        ActionType actionType;
        bytes32 offchainId;
        uint256 eventoId;
        uint256 issuedAt;
    }

    struct MintBatchParams {
        address to;
        string uri;
        bytes32 offchainId;
        ActionType actionType;
        address institutionWallet;
    }

    uint256 private _nextTokenId;

    /// @dev offchainId => tokenId (idempotência para mint direto)
    mapping(bytes32 => uint256) public offchainToToken;

    /// @dev tokenId => record
    mapping(uint256 => EventoNFTRecord) private _records;

    /// @dev eventoId => Merkle Root (para batch claim)
    mapping(uint256 => bytes32) public eventoMerkleRoot;

    /// @dev eventoId => cidadao => já reclamou?
    mapping(uint256 => mapping(address => bool)) public claimed;

    // ── Events ───────────────────────────────────────────────────────────────

    event NFTEventoMintado(
        uint256 indexed tokenId,
        address indexed citizen,
        address indexed institutionWallet,
        ActionType actionType,
        bytes32 offchainId,
        uint256 eventoId
    );

    event BatchMinted(
        bytes32 indexed eventHash,
        address institution,
        uint256 count
    );

    event MerkleRootSet(
        uint256 indexed eventoId,
        bytes32 root,
        address indexed institute
    );

    event NFTClaimed(
        uint256 indexed tokenId,
        uint256 indexed eventoId,
        address indexed citizen
    );

    /// @custom:oz-upgrades-unsafe-allow constructor
    constructor() {
        _disableInitializers();
    }

    function initialize(address admin, address minter) public initializer {
        __ERC721_init("EcoProof Evento", "ECOE");
        __ERC721URIStorage_init();
        __AccessControl_init();
        __Pausable_init();

        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(UPGRADER_ROLE, admin);
        _grantRole(PAUSER_ROLE, admin);
        _grantRole(MINTER_ROLE, minter);
    }

    // ── Soulbound: bloqueia transferências ───────────────────────────────────

    function _update(
        address to,
        uint256 tokenId,
        address auth
    ) internal override returns (address) {
        address from = _ownerOf(tokenId);
        if (from != address(0) && to != address(0)) {
            revert SoulboundNaoTransferivel();
        }
        return super._update(to, tokenId, auth);
    }

    function locked(uint256 tokenId) external view override returns (bool) {
        _requireOwned(tokenId);
        return true;
    }

    // ── Mint direto pelo backend (MINTER_ROLE) ──────────────────────────────

    function mintEvento(
        address to,
        string calldata uri,
        bytes32 offchainId,
        ActionType actionType,
        address institutionWallet,
        uint256 eventoId
    ) external onlyRole(MINTER_ROLE) whenNotPaused nonReentrant returns (uint256 tokenId) {
        if (isMinted(offchainId)) revert AlreadyMinted(offchainId);

        tokenId = _mintSoulbound(to, uri, offchainId, actionType, institutionWallet, eventoId);
    }

    // ── Mint em lote pelo backend ────────────────────────────────────────────

    function mintBatch(
        MintBatchParams[] calldata params,
        bytes32 eventHash,
        uint256 eventoId
    ) external onlyRole(MINTER_ROLE) whenNotPaused nonReentrant returns (uint256[] memory tokenIds) {
        uint256 len = params.length;
        if (len == 0) revert EmptyBatch();
        if (len > 500) revert InvalidBatchSize();

        tokenIds = new uint256[](len);
        uint256 minted = 0;
        address lastInstitution;

        for (uint256 i = 0; i < len; ) {
            MintBatchParams calldata p = params[i];

            if (!isMinted(p.offchainId) && p.to != address(0)) {
                uint256 tokenId = _mintSoulbound(
                    p.to, p.uri, p.offchainId, p.actionType, p.institutionWallet, eventoId
                );
                tokenIds[i] = tokenId;
                lastInstitution = p.institutionWallet;
                unchecked { ++minted; }
            }
            unchecked { ++i; }
        }

        emit BatchMinted(eventHash, lastInstitution, minted);
    }

    // ── Merkle Tree: Instituto registra root ─────────────────────────────────

    /**
     * @notice Instituto registra o Merkle Root para um evento.
     * @dev O root codifica a lista de endereços elegíveis.
     *      Custo: O(1) gas, independente do número de participantes.
     */
    function setMerkleRoot(
        uint256 eventoId,
        bytes32 root
    ) external onlyRole(INSTITUTE_ROLE) whenNotPaused {
        eventoMerkleRoot[eventoId] = root;
        emit MerkleRootSet(eventoId, root, msg.sender);
    }

    /**
     * @notice Cidadão reclama o próprio NFT com Merkle Proof.
     * @dev Cada cidadão paga o próprio gas para reclamar.
     *      O instituto só paga para registrar o root.
     */
    function claimNFT(
        uint256 eventoId,
        bytes32[] calldata proof,
        string calldata tokenURI_
    ) external whenNotPaused nonReentrant returns (uint256 tokenId) {
        bytes32 root = eventoMerkleRoot[eventoId];
        if (root == bytes32(0)) revert MerkleRootNotSet(eventoId);
        if (claimed[eventoId][msg.sender]) revert AlreadyClaimed(eventoId, msg.sender);

        // Verifica inclusão na Merkle Tree
        bytes32 leaf = keccak256(abi.encodePacked(msg.sender));
        if (!MerkleProof.verify(proof, root, leaf)) revert InvalidMerkleProof();

        claimed[eventoId][msg.sender] = true;

        // Mint do NFT Soulbound
        tokenId = ++_nextTokenId;
        _safeMint(msg.sender, tokenId);
        _setTokenURI(tokenId, tokenURI_);

        _records[tokenId] = EventoNFTRecord({
            citizen: msg.sender,
            institutionWallet: address(0), // definido pelo instituto via root
            actionType: ActionType.OUTRO,
            offchainId: bytes32(0),
            eventoId: eventoId,
            issuedAt: block.timestamp
        });

        emit NFTClaimed(tokenId, eventoId, msg.sender);
        emit Locked(tokenId);
    }

    // ── Internal ─────────────────────────────────────────────────────────────

    function _mintSoulbound(
        address to,
        string calldata uri,
        bytes32 offchainId,
        ActionType actionType,
        address institutionWallet,
        uint256 eventoId
    ) internal returns (uint256 tokenId) {
        tokenId = ++_nextTokenId;
        _safeMint(to, tokenId);
        _setTokenURI(tokenId, uri);

        _records[tokenId] = EventoNFTRecord({
            citizen: to,
            institutionWallet: institutionWallet,
            actionType: actionType,
            offchainId: offchainId,
            eventoId: eventoId,
            issuedAt: block.timestamp
        });

        offchainToToken[offchainId] = tokenId;

        emit NFTEventoMintado(tokenId, to, institutionWallet, actionType, offchainId, eventoId);
        emit Locked(tokenId);
    }

    // ── Views ────────────────────────────────────────────────────────────────

    function isMinted(bytes32 offchainId) public view returns (bool) {
        return offchainToToken[offchainId] != 0;
    }

    function getRecord(uint256 tokenId) external view returns (EventoNFTRecord memory) {
        _requireOwned(tokenId);
        return _records[tokenId];
    }

    function totalSupply() external view returns (uint256) {
        return _nextTokenId;
    }

    // ── Pausable ─────────────────────────────────────────────────────────────

    function pause() external onlyRole(PAUSER_ROLE) {
        _pause();
    }

    function unpause() external onlyRole(PAUSER_ROLE) {
        _unpause();
    }

    // ── UUPS ─────────────────────────────────────────────────────────────────

    function _authorizeUpgrade(address)
        internal
        override
        onlyRole(UPGRADER_ROLE)
    {}

    // ── ERC165 ───────────────────────────────────────────────────────────────

    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(ERC721URIStorageUpgradeable, AccessControlUpgradeable)
        returns (bool)
    {
        return interfaceId == 0xb45a3c0e || super.supportsInterface(interfaceId);
    }
}
