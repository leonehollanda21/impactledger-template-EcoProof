// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts-upgradeable/token/ERC721/extensions/ERC721URIStorageUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/access/AccessControlUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/utils/PausableUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/Initializable.sol";

// Custom Errors 
error AlreadyMinted(bytes32 offchainId);
error InvalidBatchSize();
error EmptyBatch();
error SoulboundNaoTransferivel();
error ReentrantCall();

// EIP-5192: Minimal Soulbound Interface 
interface IERC5192 {
    event Locked(uint256 tokenId);
    event Unlocked(uint256 tokenId);
    function locked(uint256 tokenId) external view returns (bool);
}

/**
 * @title EcoProofNFT (ECOI — EcoProof Individual)
 * @notice Soulbound Token (SBT) para ações ambientais individuais.
 */
contract EcoProofNFT is
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

    uint256 private constant _NOT_ENTERED = 1;
    uint256 private constant _ENTERED = 2;
    uint256 private _reentrancyStatus;

    modifier nonReentrant() {
        if (_reentrancyStatus == _ENTERED) revert ReentrantCall();
        _reentrancyStatus = _ENTERED;
        _;
        _reentrancyStatus = _NOT_ENTERED;
    }

    enum ActionType { LIXO_RUA, PRAIA, CORREGO, QUEIMADA, OUTRO, EDUCACAO, ADOCAO }
    enum IssuedBy { ECOPROOF, INSTITUTO }

    struct NFTRecord {
        address citizen;
        ActionType actionType;
        IssuedBy issuedBy;
        uint64 issuedAt;

        address institutionWallet;
        uint64 aiScore;

        bytes32 offchainId;
    }

    struct MintBatchParams {
        address to;
        string uri;
        bytes32 offchainId;
        ActionType actionType;
        address institutionWallet;
    }

    uint256 private _nextTokenId;
    
    mapping(bytes32 => uint256) public offchainToToken;
    mapping(uint256 => NFTRecord) private _records;

    // Events
    event ActionMinted(
        uint256 indexed tokenId, 
        address indexed citizen, 
        ActionType actionType, 
        IssuedBy issuedBy, 
        bytes32 indexed offchainId, 
        uint256 aiScore
    );
    event BatchMinted(bytes32 indexed eventHash, address institution, uint256 count);
    event GuardiaoMinted(uint256 indexed tokenId, address indexed citizen, bytes32 indexed adoptionId); 

    /// @custom:oz-upgrades-unsafe-allow constructor
    constructor() {
        _disableInitializers();
    }

    function initialize(address admin, address minter) public initializer {
        __ERC721_init("EcoProof Individual", "ECOI");
        __ERC721URIStorage_init();
        __AccessControl_init();
        __Pausable_init();

        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(UPGRADER_ROLE, admin);
        _grantRole(PAUSER_ROLE, admin);
        _grantRole(MINTER_ROLE, minter);

        _reentrancyStatus = _NOT_ENTERED;
    }

    // Soulbound 
    function _update(address to, uint256 tokenId, address auth) internal override returns (address) {
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

    // Mint: Limpeza Individual
    function mintLimpeza(
        address to,
        string calldata uri,
        bytes32 offchainId,
        ActionType actionType,
        uint64 aiScore
    ) external onlyRole(MINTER_ROLE) whenNotPaused nonReentrant returns (uint256 tokenId) {
        if (isMinted(offchainId)) revert AlreadyMinted(offchainId);

        tokenId = ++_nextTokenId;
        _safeMint(to, tokenId);
        _setTokenURI(tokenId, uri);

        _records[tokenId] = NFTRecord({
            citizen: to,
            actionType: actionType,
            issuedBy: IssuedBy.ECOPROOF,
            issuedAt: uint64(block.timestamp),
            institutionWallet: address(0),
            aiScore: aiScore,
            offchainId: offchainId
        });

        offchainToToken[offchainId] = tokenId;

        emit ActionMinted(tokenId, to, actionType, IssuedBy.ECOPROOF, offchainId, aiScore);
        emit Locked(tokenId);
    }

    // Mint: Participação em Evento 
    function mintEvento(
        address to,
        string calldata uri,
        bytes32 offchainId,
        ActionType actionType,
        address institutionWallet
    ) external onlyRole(MINTER_ROLE) whenNotPaused nonReentrant returns (uint256 tokenId) {
        if (isMinted(offchainId)) revert AlreadyMinted(offchainId);

        tokenId = ++_nextTokenId;
        _safeMint(to, tokenId);
        _setTokenURI(tokenId, uri);

        _records[tokenId] = NFTRecord({
            citizen: to,
            actionType: actionType,
            issuedBy: IssuedBy.INSTITUTO,
            issuedAt: uint64(block.timestamp),
            institutionWallet: institutionWallet,
            aiScore: 0,
            offchainId: offchainId
        });

        offchainToToken[offchainId] = tokenId;

        emit ActionMinted(tokenId, to, actionType, IssuedBy.INSTITUTO, offchainId, 0);
        emit Locked(tokenId);
    }

    // Mint: Guardião (Adoção) 
    function mintGuardiao(
        address to,
        string calldata uri,
        bytes32 adoptionId
    ) external onlyRole(MINTER_ROLE) whenNotPaused nonReentrant returns (uint256 tokenId) {
        if (isMinted(adoptionId)) revert AlreadyMinted(adoptionId);

        tokenId = ++_nextTokenId;
        _safeMint(to, tokenId);
        _setTokenURI(tokenId, uri);

        _records[tokenId] = NFTRecord({
            citizen: to,
            actionType: ActionType.ADOCAO,
            issuedBy: IssuedBy.ECOPROOF,
            issuedAt: uint64(block.timestamp),
            institutionWallet: address(0),
            aiScore: 0,
            offchainId: adoptionId
        });

        offchainToToken[adoptionId] = tokenId;

        emit GuardiaoMinted(tokenId, to, adoptionId);
        emit Locked(tokenId);
    }

    // Mint em lote 
    function mintBatch(
        MintBatchParams[] calldata params,
        bytes32 eventHash
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
                uint256 tokenId = ++_nextTokenId;

                _safeMint(p.to, tokenId);
                _setTokenURI(tokenId, p.uri);

                _records[tokenId] = NFTRecord({
                    citizen: p.to,
                    actionType: p.actionType,
                    issuedBy: IssuedBy.INSTITUTO,
                    issuedAt: uint64(block.timestamp),
                    institutionWallet: p.institutionWallet,
                    aiScore: 0,
                    offchainId: p.offchainId
                });

                offchainToToken[p.offchainId] = tokenId;
                tokenIds[i] = tokenId;

                emit ActionMinted(tokenId, p.to, p.actionType, IssuedBy.INSTITUTO, p.offchainId, 0);
                emit Locked(tokenId);

                lastInstitution = p.institutionWallet;
                unchecked { ++minted; }
            }
            unchecked { ++i; }
        }

        emit BatchMinted(eventHash, lastInstitution, minted);
    }

    //Views & Utils

    function isMinted(bytes32 offchainId) public view returns (bool) {
        return offchainToToken[offchainId] != 0;
    }

    function getRecord(uint256 tokenId) external view returns (NFTRecord memory) {
        _requireOwned(tokenId);
        return _records[tokenId];
    }

    function totalSupply() external view returns (uint256) {
        return _nextTokenId;
    }

    function pause() external onlyRole(PAUSER_ROLE) {
        _pause();
    }

    function unpause() external onlyRole(PAUSER_ROLE) {
        _unpause();
    }

    function _authorizeUpgrade(address) internal override onlyRole(UPGRADER_ROLE) {}

    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(ERC721URIStorageUpgradeable, AccessControlUpgradeable)
        returns (bool)
    {
        return interfaceId == 0xb45a3c0e || super.supportsInterface(interfaceId);
    }
}