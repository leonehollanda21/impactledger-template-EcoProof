// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts-upgradeable/token/ERC721/extensions/ERC721URIStorageUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/access/AccessControlUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/utils/PausableUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/Initializable.sol";

// ── Custom Errors ────────────────────────────────────────────────────────────
error AlreadyMinted(bytes32 offchainId);
error InvalidBatchSize();
error EmptyBatch();
error SoulboundNaoTransferivel();
error ReentrantCall();
error InvalidImpactCount();

// ── EIP-5192: Minimal Soulbound Interface ────────────────────────────────────
interface IERC5192 {
    event Locked(uint256 tokenId);
    event Unlocked(uint256 tokenId);
    function locked(uint256 tokenId) external view returns (bool);
}

/**
 * @title EducacaoNFT (ECED — EcoProof Educação)
 * @notice Soulbound Token (SBT) para ações de educação ambiental.
 * @dev Implementa EIP-5192 para tokens intransferíveis.
 *
 *      Diferencial em relação aos demais contratos:
 *      - Impacto medido em PESSOAS, não em área/ambiente.
 *      - Cada NFT registra o número de participantes impactados (impactCount).
 *      - Validação pode vir do Instituto (ação institucional) ou do Admin (ação cidadã).
 *      - Título do NFT: "Educador Ambiental — X pessoas impactadas"
 *
 *      Tipos de ação educativa:
 *      - PALESTRA: Palestra em escola ou comunidade
 *      - OFICINA: Oficina de reciclagem, compostagem, etc.
 *      - RODA_CONVERSA: Roda de conversa sobre sustentabilidade
 *      - MUTIRAO_EDUCATIVO: Mutirão com componente educativo
 *      - OUTRO: Outras ações educativas
 *
 *      Fluxo:
 *      1. Cidadão/Instituto realiza ação educativa e envia foto + nº participantes
 *      2. Instituto valida (se ação institucional) ou Admin valida (se ação cidadã)
 *      3. Backend chama mintEducacao() com impactCount
 *      4. NFT Soulbound é gerado com impacto social registrado on-chain
 */
contract EducacaoNFT is
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

    enum EducacaoType { PALESTRA, OFICINA, RODA_CONVERSA, MUTIRAO_EDUCATIVO, OUTRO }
    enum IssuedBy { ADMIN, INSTITUTO }

    struct EducacaoRecord {
        address citizen;               
        EducacaoType educacaoType;     
        IssuedBy issuedBy;             
        uint64 issuedAt;               

        address validatorWallet;       
        uint32 impactCount;            

        bytes32 offchainId;            
    }

    struct MintBatchParams {
        address to;
        string uri;
        bytes32 offchainId;
        EducacaoType educacaoType;
        address validatorWallet;
        uint32 impactCount;
    }

    uint256 private _nextTokenId;

    /// @dev offchainId => tokenId (idempotência)
    mapping(bytes32 => uint256) public offchainToToken;

    /// @dev tokenId => record
    mapping(uint256 => EducacaoRecord) private _records;

    /// @dev Total de pessoas impactadas (soma global de todos os NFTs)
    uint256 public totalPeopleImpacted;

    // Events 

    event EducacaoMinted(
        uint256 indexed tokenId,
        address indexed citizen,
        EducacaoType educacaoType,
        IssuedBy issuedBy,
        bytes32 indexed offchainId,
        uint32 impactCount
    );

    event BatchEducacaoMinted(
        bytes32 indexed eventHash,
        address validator,
        uint256 count,
        uint256 totalImpact
    );

    /// @custom:oz-upgrades-unsafe-allow constructor
    constructor() {
        _disableInitializers();
    }

    function initialize(address admin, address minter) public initializer {
        __ERC721_init("EcoProof Educacao", "ECED");
        __ERC721URIStorage_init();
        __AccessControl_init();
        __Pausable_init();

        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(UPGRADER_ROLE, admin);
        _grantRole(PAUSER_ROLE, admin);
        _grantRole(MINTER_ROLE, minter);

        _reentrancyStatus = _NOT_ENTERED;
    }

    // Soulbound: bloqueia transferências 

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

    // Mint: Educação Ambiental (individual)

    /**
     * @notice Minta um NFT de educação ambiental para o cidadão.
     * @param to Endereço do cidadão educador
     * @param uri URI dos metadados (IPFS/API)
     * @param offchainId UUID único do registro off-chain
     * @param educacaoType Tipo da ação educativa
     * @param validatorWallet Wallet do instituto/admin que validou
     * @param impactCount Número de pessoas impactadas pela ação
     * @param issuedBy Quem validou: ADMIN ou INSTITUTO
     * @return tokenId ID do token mintado
     */
    function mintEducacao(
        address to,
        string calldata uri,
        bytes32 offchainId,
        EducacaoType educacaoType,
        address validatorWallet,
        uint32 impactCount,
        IssuedBy issuedBy
    ) external onlyRole(MINTER_ROLE) whenNotPaused nonReentrant returns (uint256 tokenId) {
        if (isMinted(offchainId)) revert AlreadyMinted(offchainId);
        if (impactCount == 0) revert InvalidImpactCount();

        tokenId = _mintSoulbound(to, uri, offchainId, educacaoType, validatorWallet, impactCount, issuedBy);
    }

    // Mint em lote 

    /**
     * @notice Minta NFTs de educação em lote (ex: vários educadores em um evento).
     * @param params Array de parâmetros para cada mint
     * @param eventHash Hash do evento off-chain (agrupamento)
     * @param issuedBy Quem validou o lote: ADMIN ou INSTITUTO
     * @return tokenIds Array de IDs dos tokens mintados
     */
    function mintBatch(
        MintBatchParams[] calldata params,
        bytes32 eventHash,
        IssuedBy issuedBy
    ) external onlyRole(MINTER_ROLE) whenNotPaused nonReentrant returns (uint256[] memory tokenIds) {
        uint256 len = params.length;
        if (len == 0) revert EmptyBatch();
        if (len > 500) revert InvalidBatchSize();

        tokenIds = new uint256[](len);
        uint256 minted = 0;
        uint256 batchImpact = 0;
        address lastValidator;

        for (uint256 i = 0; i < len; ) {
            MintBatchParams calldata p = params[i];

            if (!isMinted(p.offchainId) && p.to != address(0) && p.impactCount > 0) {
                uint256 tokenId = _mintSoulbound(
                    p.to, p.uri, p.offchainId, p.educacaoType,
                    p.validatorWallet, p.impactCount, issuedBy
                );
                tokenIds[i] = tokenId;
                lastValidator = p.validatorWallet;
                unchecked {
                    batchImpact += p.impactCount;
                    ++minted;
                }
            }
            unchecked { ++i; }
        }

        emit BatchEducacaoMinted(eventHash, lastValidator, minted, batchImpact);
    }

    // Internal 

    function _mintSoulbound(
        address to,
        string calldata uri,
        bytes32 offchainId,
        EducacaoType educacaoType,
        address validatorWallet,
        uint32 impactCount,
        IssuedBy issuedBy
    ) internal returns (uint256 tokenId) {
        tokenId = ++_nextTokenId;
        _safeMint(to, tokenId);
        _setTokenURI(tokenId, uri);

        _records[tokenId] = EducacaoRecord({
            citizen: to,
            educacaoType: educacaoType,
            issuedBy: issuedBy,
            issuedAt: uint64(block.timestamp),
            validatorWallet: validatorWallet,
            impactCount: impactCount,
            offchainId: offchainId
        });

        offchainToToken[offchainId] = tokenId;

        unchecked {
            totalPeopleImpacted += impactCount;
        }

        emit EducacaoMinted(tokenId, to, educacaoType, issuedBy, offchainId, impactCount);
        emit Locked(tokenId);
    }

    // Views & Utils 

    function isMinted(bytes32 offchainId) public view returns (bool) {
        return offchainToToken[offchainId] != 0;
    }

    function getRecord(uint256 tokenId) external view returns (EducacaoRecord memory) {
        _requireOwned(tokenId);
        return _records[tokenId];
    }

    function totalSupply() external view returns (uint256) {
        return _nextTokenId;
    }

    // Pausable 

    function pause() external onlyRole(PAUSER_ROLE) {
        _pause();
    }

    function unpause() external onlyRole(PAUSER_ROLE) {
        _unpause();
    }

    // UUPS 

    function _authorizeUpgrade(address) internal override onlyRole(UPGRADER_ROLE) {}

    // ERC165

    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(ERC721URIStorageUpgradeable, AccessControlUpgradeable)
        returns (bool)
    {
        return interfaceId == 0xb45a3c0e || super.supportsInterface(interfaceId);
    }
}
