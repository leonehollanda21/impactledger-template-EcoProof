// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/AccessControl.sol";

// ── Custom Errors ────────────────────────────────────────────────────────────
error InvalidAddress();
error AlreadyRegistered(bytes32 offchainId);
error InvalidHash();
error ProofNotFound(bytes32 offchainId);
error InvalidCheckInMonth(uint8 expected, uint8 received);
error AdoptionAlreadyCompleted(bytes32 adoptionId);

/**
 * @title EcoProofRegistry (ValidationRegistry)
 * @notice Registro imutável de todas as validações — Proof of Existence.
 */
contract EcoProofRegistry is AccessControl {
    bytes32 public constant VALIDATOR_ROLE = keccak256("VALIDATOR_ROLE");

    enum ActionType { LIXO_RUA, PRAIA, CORREGO, QUEIMADA, OUTRO, EDUCACAO, ADOCAO }

    struct Proof {
        bytes32 photoAfterHash;   
        bytes32 photoBeforeHash;   
        bytes32 metadataHash;      
        address validador;        
        uint64  aiScore;
        uint32  impactCount;
        uint64  timestamp;
        ActionType actionType;
        bool    aprovado;
        bool    exists;
    }

    struct AdoptionProof {
        bytes32[4] photoHashes; // [0: Início, 1: Mês 1, 2: Mês 2, 3: Mês 3]
        uint64 startTimestamp;
        uint64 lastCheckInTimestamp;
        uint8 checkInsCompleted; // Contador de 0 a 3
        bool exists;
    }

    mapping(bytes32 => Proof) private _proofs;
    mapping(bytes32 => AdoptionProof) private _adoptions;
    uint256 public totalProofs;

    event ProofRegistered(
        bytes32 indexed offchainId,
        bytes32 photoHash,
        address indexed validador,
        bool    aprovado,
        ActionType actionType,
        uint64  aiScore
    );

    event LimpezaRegistered(
        bytes32 indexed offchainId,
        ActionType actionType,
        uint64 aiScore
    );

    event ParticipacaoRegistered(
        bytes32 indexed offchainId,
        ActionType actionType
    );
    event EducacaoRegistered(
        bytes32 indexed offchainId, 
        uint32 impactCount
    );
    event AdocaoCheckInRegistered(bytes32 indexed adoptionId,
        uint8 month,
        bytes32 photoHash
    );

    constructor(address admin, address validator) {
        if (admin == address(0) || validator == address(0)) revert InvalidAddress();

        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(VALIDATOR_ROLE, validator);
    }

    // ── Register: Limpeza ────────────────────────────────────────────────────

    function registerLimpeza(
        bytes32 offchainId,
        bytes32 photoAfterHash,
        bytes32 photoBeforeHash,
        bytes32 metadataHash,
        uint64  aiScore,
        ActionType actionType,
        bool    aprovado
    ) external onlyRole(VALIDATOR_ROLE) {
        if (_proofs[offchainId].exists) revert AlreadyRegistered(offchainId);
        if (photoAfterHash == bytes32(0) || photoBeforeHash == bytes32(0)) revert InvalidHash();

        _proofs[offchainId] = Proof({
            photoAfterHash:  photoAfterHash,
            photoBeforeHash: photoBeforeHash,
            metadataHash:    metadataHash,
            validador:       msg.sender,
            aiScore:         aiScore,
            impactCount:     0,
            timestamp:       uint64(block.timestamp),
            actionType:      actionType,
            aprovado:        aprovado,
            exists:          true
        });

        unchecked { ++totalProofs; }

        emit ProofRegistered(offchainId, photoAfterHash, msg.sender, aprovado, actionType, aiScore);
        emit LimpezaRegistered(offchainId, actionType, aiScore);
    }

    // ── Register: Participação ───────────────────────────────────────────────

    function registerParticipacao(
        bytes32 offchainId,
        bytes32 photoHash,
        bytes32 metadataHash,
        ActionType actionType
    ) external onlyRole(VALIDATOR_ROLE) {
        if (_proofs[offchainId].exists) revert AlreadyRegistered(offchainId);
        if (photoHash == bytes32(0)) revert InvalidHash();

        _proofs[offchainId] = Proof({
            photoAfterHash:  photoHash,
            photoBeforeHash: bytes32(0),
            metadataHash:    metadataHash,
            validador:       msg.sender,
            aiScore:         0,
            impactCount:     0,
            timestamp:       uint64(block.timestamp),
            actionType:      actionType,
            aprovado:        true,
            exists:          true
        });

        unchecked { ++totalProofs; }

        emit ProofRegistered(offchainId, photoHash, msg.sender, true, actionType, 0);
        emit ParticipacaoRegistered(offchainId, actionType);
    }

    // ── Register: Educação Ambiental ─────────────────────────────────────────

    function registerEducacao(
        bytes32 offchainId,
        bytes32 photoHash,
        bytes32 metadataHash,
        uint32 impactCount
    ) external onlyRole(VALIDATOR_ROLE) {
        if (_proofs[offchainId].exists) revert AlreadyRegistered(offchainId);
        if (photoHash == bytes32(0)) revert InvalidHash();

        _proofs[offchainId] = Proof({
            photoAfterHash:  photoHash,
            photoBeforeHash: bytes32(0),
            metadataHash:    metadataHash,
            validador:       msg.sender,
            aiScore:         0,
            impactCount:     impactCount,
            timestamp:       uint64(block.timestamp),
            actionType:      ActionType.EDUCACAO,
            aprovado:        true,
            exists:          true
        });

        unchecked { ++totalProofs; }

        emit ProofRegistered(offchainId, photoHash, msg.sender, true, ActionType.EDUCACAO, 0);
        emit EducacaoRegistered(offchainId, impactCount);
    }

    // ── Register: Adoção (Máquina de Estados) ────────────────────────────────

    function registerAdocaoCheckIn(
        bytes32 adoptionId,
        uint8 month,
        bytes32 photoHash
    ) external onlyRole(VALIDATOR_ROLE) {
        if (photoHash == bytes32(0)) revert InvalidHash();
        
        AdoptionProof storage adoption = _adoptions[adoptionId];

        if (!adoption.exists) {
            // Início da adoção
            if (month != 0) revert InvalidCheckInMonth(0, month);
            
            adoption.photoHashes[0] = photoHash;
            adoption.startTimestamp = uint64(block.timestamp);
            adoption.lastCheckInTimestamp = uint64(block.timestamp);
            adoption.checkInsCompleted = 0;
            adoption.exists = true;
        } else {
            // Meses 1, 2 e 3
            if (adoption.checkInsCompleted >= 3) revert AdoptionAlreadyCompleted(adoptionId);
            uint8 expectedMonth = adoption.checkInsCompleted + 1;
            if (month != expectedMonth) revert InvalidCheckInMonth(expectedMonth, month);

            adoption.photoHashes[month] = photoHash;
            adoption.lastCheckInTimestamp = uint64(block.timestamp);
            adoption.checkInsCompleted = month;
        }

        emit AdocaoCheckInRegistered(adoptionId, month, photoHash);
    }

    // ── Views ────────────────────────────────────────────────────────────────

    function getAdoption(bytes32 adoptionId) external view returns (AdoptionProof memory) {
        if (!_adoptions[adoptionId].exists) revert ProofNotFound(adoptionId);
        return _adoptions[adoptionId];
    }

    function verifyPhoto(bytes32 offchainId, bytes32 photoHash) external view returns (bool) {
        Proof storage p = _proofs[offchainId];
        if (!p.exists) return false;
        return p.photoAfterHash == photoHash || p.photoBeforeHash == photoHash;
    }

    function verifyMetadata(bytes32 offchainId, bytes32 metadataHash_) external view returns (bool) {
        Proof storage p = _proofs[offchainId];
        if (!p.exists) return false;
        return p.metadataHash == metadataHash_;
    }

    function getProof(bytes32 offchainId) external view returns (Proof memory) {
        if (!_proofs[offchainId].exists) revert ProofNotFound(offchainId);
        return _proofs[offchainId];
    }

    function isRegistered(bytes32 offchainId) external view returns (bool) {
        return _proofs[offchainId].exists;
    }
}