// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts-upgradeable/token/ERC721/extensions/ERC721URIStorageUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/access/AccessControlUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/utils/PausableUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/Initializable.sol";

// ── Custom Errors ────────────────────────────────────────────────────────────
error AlreadyRegistered(bytes32 offchainId);
error DenunciaNotRegistered(bytes32 offchainId);
error DenunciaAlreadyResolved(bytes32 offchainId);
error SoulboundNaoTransferivel();
error ReentrantCall();
error InvalidAddress();
error InvalidHash();
error InvalidDescription();
error InvalidURI();

// ── EIP-5192: Minimal Soulbound Interface ────────────────────────────────────
interface IERC5192 {
    event Locked(uint256 tokenId);
    event Unlocked(uint256 tokenId);
    function locked(uint256 tokenId) external view returns (bool);
}

/**
 * @title DenunciaNFT (ECFD — EcoProof Denúncia)
 * @notice Soulbound Token (SBT) para denúncias ambientais verificadas.
 * @dev Implementa EIP-5192 para tokens intransferíveis.
 *
 *      Fluxo:
 *      1. Cidadão fotografa e reporta um problema ambiental (foto + descrição).
 *      2. A denúncia é registrada on-chain (registrarDenuncia) pelo backend/admin (MINTER_ROLE).
 *      3. Quando resolvida, a confirmação (foto do depois) é enviada via resolverDenuncia.
 *      4. O NFT Soulbound "Fiscal Ambiental — Denúncia #[ID] Resolvida" é gerado para o cidadão.
 */
contract DenunciaNFT is
    Initializable,
    ERC721URIStorageUpgradeable,
    AccessControlUpgradeable,
    PausableUpgradeable,
    UUPSUpgradeable,
    IERC5192
{
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
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

    enum Status { REPORTADA, RESOLVIDA }

    struct DenunciaRecord {
        address citizen;               // Cidadão que fez a denúncia
        bytes32 offchainId;            // UUID único do registro off-chain
        bytes32 photoBeforeHash;       // Hash da foto do problema (antes)
        bytes32 photoAfterHash;        // Hash da foto do problema resolvido (depois)
        string description;            // Descrição do problema
        Status status;                 // Status atual: REPORTADA ou RESOLVIDA
        uint64 reportedAt;             // Timestamp de quando foi reportado
        uint64 resolvedAt;             // Timestamp de quando foi resolvido
        uint256 tokenId;               // ID do NFT gerado (0 se ainda não resolvido)
    }

    uint256 private _nextTokenId;

    /// @dev offchainId => DenunciaRecord
    mapping(bytes32 => DenunciaRecord) private _denuncias;

    /// @dev offchainId => status do registro (se existe)
    mapping(bytes32 => bool) public isRegistered;

    /// @dev Total de denúncias resolvidas
    uint256 public totalResolved;

    /// @dev Total de denúncias reportadas
    uint256 public totalReported;

    // ── Events ───────────────────────────────────────────────────────────────

    event DenunciaRegistrada(
        bytes32 indexed offchainId,
        address indexed citizen,
        bytes32 photoBeforeHash,
        string description
    );

    event DenunciaResolvida(
        bytes32 indexed offchainId,
        uint256 indexed tokenId,
        bytes32 photoAfterHash
    );

    /// @custom:oz-upgrades-unsafe-allow constructor
    constructor() {
        _disableInitializers();
    }

    function initialize(address admin, address minter) public initializer {
        __ERC721_init("EcoProof Denuncia", "ECFD");
        __ERC721URIStorage_init();
        __AccessControl_init();
        __Pausable_init();

        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(UPGRADER_ROLE, admin);
        _grantRole(PAUSER_ROLE, admin);
        _grantRole(MINTER_ROLE, minter);

        _reentrancyStatus = _NOT_ENTERED;
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

    // ── Registro de Denúncia ─────────────────────────────────────────────────

    /**
     * @notice Registra uma nova denúncia na blockchain.
     * @param citizen Endereço do cidadão fiscalizador
     * @param offchainId UUID único do registro off-chain
     * @param photoBeforeHash Hash da foto do problema
     * @param description Descrição textual do problema ambiental
     */
    function registrarDenuncia(
        address citizen,
        bytes32 offchainId,
        bytes32 photoBeforeHash,
        string calldata description
    ) external onlyRole(MINTER_ROLE) whenNotPaused nonReentrant {
        if (citizen == address(0)) revert InvalidAddress();
        if (offchainId == bytes32(0)) revert InvalidHash();
        if (photoBeforeHash == bytes32(0)) revert InvalidHash();
        if (bytes(description).length == 0) revert InvalidDescription();
        if (isRegistered[offchainId]) revert AlreadyRegistered(offchainId);

        _denuncias[offchainId] = DenunciaRecord({
            citizen: citizen,
            offchainId: offchainId,
            photoBeforeHash: photoBeforeHash,
            photoAfterHash: bytes32(0),
            description: description,
            status: Status.REPORTADA,
            reportedAt: uint64(block.timestamp),
            resolvedAt: 0,
            tokenId: 0
        });

        isRegistered[offchainId] = true;
        totalReported++;

        emit DenunciaRegistrada(offchainId, citizen, photoBeforeHash, description);
    }

    // ── Resolução de Denúncia & Mint ──────────────────────────────────────────

    /**
     * @notice Resolve uma denúncia reportando a foto de confirmação e mintando o NFT.
     * @param offchainId UUID único do registro off-chain da denúncia
     * @param photoAfterHash Hash da foto de confirmação do problema resolvido
     * @param uri URI dos metadados (IPFS/API)
     * @return tokenId ID do token mintado
     */
    function resolverDenuncia(
        bytes32 offchainId,
        bytes32 photoAfterHash,
        string calldata uri
    ) external onlyRole(MINTER_ROLE) whenNotPaused nonReentrant returns (uint256 tokenId) {
        if (!isRegistered[offchainId]) revert DenunciaNotRegistered(offchainId);
        
        DenunciaRecord storage record = _denuncias[offchainId];
        if (record.status == Status.RESOLVIDA) revert DenunciaAlreadyResolved(offchainId);
        if (photoAfterHash == bytes32(0)) revert InvalidHash();
        if (bytes(uri).length == 0) revert InvalidURI();

        tokenId = ++_nextTokenId;
        _safeMint(record.citizen, tokenId);
        _setTokenURI(tokenId, uri);

        record.status = Status.RESOLVIDA;
        record.photoAfterHash = photoAfterHash;
        record.resolvedAt = uint64(block.timestamp);
        record.tokenId = tokenId;

        totalResolved++;

        emit DenunciaResolvida(offchainId, tokenId, photoAfterHash);
        emit Locked(tokenId);
    }

    // ── Views & Utils ────────────────────────────────────────────────────────

    function getDenuncia(bytes32 offchainId) external view returns (DenunciaRecord memory) {
        if (!isRegistered[offchainId]) revert DenunciaNotRegistered(offchainId);
        return _denuncias[offchainId];
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

    function _authorizeUpgrade(address) internal override onlyRole(UPGRADER_ROLE) {}

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
