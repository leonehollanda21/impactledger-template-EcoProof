const { expect } = require("chai");
const { ethers } = require("hardhat");
const { loadFixture } = require("@nomicfoundation/hardhat-network-helpers");

function toBytes32(str) {
    return ethers.keccak256(ethers.toUtf8Bytes(str));
}

describe("EcoProofRegistry (ValidationRegistry — Proof of Existence)", function () {
    const ActionType = { LIXO_RUA: 0, PRAIA: 1, CORREGO: 2, QUEIMADA: 3, OUTRO: 4, EDUCACAO: 5, ADOCAO: 6 };

    const LIMPEZA_UUID = "limpeza-uuid-001";
    const PARTICIPACAO_UUID = "participacao-uuid-001";

    const PHOTO_AFTER_HASH = ethers.keccak256(ethers.toUtf8Bytes("conteudo-foto-depois"));
    const PHOTO_BEFORE_HASH = ethers.keccak256(ethers.toUtf8Bytes("conteudo-foto-antes"));
    const METADATA_HASH = ethers.keccak256(ethers.toUtf8Bytes("metadata-json-content"));
    const PARTICIPACAO_HASH = ethers.keccak256(ethers.toUtf8Bytes("conteudo-foto-participacao"));

    async function deployRegistryFixture() {
        const [admin, validator, stranger] = await ethers.getSigners();

        const Registry = await ethers.getContractFactory("EcoProofRegistry");
        const registry = await Registry.deploy(admin.address, validator.address);

        return { registry, admin, validator, stranger, Registry };
    }

    describe("Deploy", function () {
        it("deve atribuir VALIDATOR_ROLE corretamente", async function () {
            const { registry, admin, validator } = await loadFixture(deployRegistryFixture);
            
            const VALIDATOR_ROLE = await registry.VALIDATOR_ROLE();
            const ADMIN_ROLE = await registry.DEFAULT_ADMIN_ROLE();

            expect(await registry.hasRole(VALIDATOR_ROLE, validator.address)).to.be.true;
            expect(await registry.hasRole(ADMIN_ROLE, admin.address)).to.be.true;
        });

        it("totalProofs deve comecar em 0", async function () {
            const { registry } = await loadFixture(deployRegistryFixture);
            expect(await registry.totalProofs()).to.equal(0n);
        });

        it("deve rejeitar admin zero no deploy", async function () {
            const { Registry, validator } = await loadFixture(deployRegistryFixture);
            
            await expect(
                Registry.deploy(ethers.ZeroAddress, validator.address)
            ).to.be.revertedWithCustomError(Registry, "InvalidAddress");
        });
    });

    describe("registerLimpeza", function () {
        it("deve registrar prova completa com metadataHash e emitir eventos", async function () {
            const { registry, validator } = await loadFixture(deployRegistryFixture);
            const offchainId = toBytes32(LIMPEZA_UUID);

            const tx = await registry.connect(validator).registerLimpeza(
                offchainId, PHOTO_AFTER_HASH, PHOTO_BEFORE_HASH, METADATA_HASH,
                87n, ActionType.PRAIA, true
            );

            await expect(tx)
                .to.emit(registry, "LimpezaRegistered")
                .withArgs(offchainId, ActionType.PRAIA, 87n);

            await expect(tx)
                .to.emit(registry, "ProofRegistered")
                .withArgs(offchainId, PHOTO_AFTER_HASH, validator.address, true, ActionType.PRAIA, 87n);

            expect(await registry.totalProofs()).to.equal(1n);
            expect(await registry.isRegistered(offchainId)).to.be.true;
        });

        it("deve armazenar a prova com todos os campos incluindo metadataHash e validador", async function () {
            const { registry, validator } = await loadFixture(deployRegistryFixture);
            const offchainId = toBytes32(LIMPEZA_UUID);
            
            await registry.connect(validator).registerLimpeza(
                offchainId, PHOTO_AFTER_HASH, PHOTO_BEFORE_HASH, METADATA_HASH,
                87n, ActionType.PRAIA, true
            );

            const proof = await registry.getProof(offchainId);
            expect(proof.photoAfterHash).to.equal(PHOTO_AFTER_HASH);
            expect(proof.photoBeforeHash).to.equal(PHOTO_BEFORE_HASH);
            expect(proof.metadataHash).to.equal(METADATA_HASH);
            expect(proof.validador).to.equal(validator.address);
            expect(proof.aiScore).to.equal(87n);
            expect(proof.actionType).to.equal(ActionType.PRAIA);
            expect(proof.aprovado).to.be.true;
            expect(proof.exists).to.be.true;
            expect(proof.timestamp).to.be.greaterThan(0n);
        });

        it("deve registrar prova de limpeza reprovada", async function () {
            const { registry, validator } = await loadFixture(deployRegistryFixture);
            const offchainId = toBytes32(LIMPEZA_UUID);
            
            await registry.connect(validator).registerLimpeza(
                offchainId, PHOTO_AFTER_HASH, PHOTO_BEFORE_HASH, METADATA_HASH,
                30n, ActionType.PRAIA, false
            );

            const proof = await registry.getProof(offchainId);
            expect(proof.aprovado).to.be.false;
            expect(proof.aiScore).to.equal(30n);
        });

        it("deve rejeitar registro duplicado garantindo idempotencia", async function () {
            const { registry, validator } = await loadFixture(deployRegistryFixture);
            const offchainId = toBytes32(LIMPEZA_UUID);
            
            await registry.connect(validator).registerLimpeza(
                offchainId, PHOTO_AFTER_HASH, PHOTO_BEFORE_HASH, METADATA_HASH,
                87n, ActionType.PRAIA, true
            );

            await expect(
                registry.connect(validator).registerLimpeza(
                    offchainId, PHOTO_AFTER_HASH, PHOTO_BEFORE_HASH, METADATA_HASH,
                    87n, ActionType.PRAIA, true
                )
            ).to.be.revertedWithCustomError(registry, "AlreadyRegistered").withArgs(offchainId);
        });

        it("deve rejeitar hash zero para foto", async function () {
            const { registry, validator } = await loadFixture(deployRegistryFixture);
            
            await expect(
                registry.connect(validator).registerLimpeza(
                    toBytes32(LIMPEZA_UUID), ethers.ZeroHash, PHOTO_BEFORE_HASH, METADATA_HASH,
                    87n, ActionType.PRAIA, true
                )
            ).to.be.revertedWithCustomError(registry, "InvalidHash");
        });

        it("deve rejeitar chamada sem VALIDATOR_ROLE", async function () {
            const { registry, stranger } = await loadFixture(deployRegistryFixture);
            const VALIDATOR_ROLE = await registry.VALIDATOR_ROLE();

            await expect(
                registry.connect(stranger).registerLimpeza(
                    toBytes32(LIMPEZA_UUID), PHOTO_AFTER_HASH, PHOTO_BEFORE_HASH, METADATA_HASH,
                    87n, ActionType.PRAIA, true
                )
            ).to.be.revertedWithCustomError(registry, "AccessControlUnauthorizedAccount")
             .withArgs(stranger.address, VALIDATOR_ROLE);
        });
    });

    describe("registerParticipacao", function () {
        it("deve registrar participacao com metadataHash e emitir eventos", async function () {
            const { registry, validator } = await loadFixture(deployRegistryFixture);
            const offchainId = toBytes32(PARTICIPACAO_UUID);

            const tx = await registry.connect(validator).registerParticipacao(
                offchainId, PARTICIPACAO_HASH, METADATA_HASH, ActionType.PRAIA
            );

            await expect(tx)
                .to.emit(registry, "ParticipacaoRegistered")
                .withArgs(offchainId, ActionType.PRAIA);

            await expect(tx)
                .to.emit(registry, "ProofRegistered");
        });

        it("photoBeforeHash deve ser zero e aprovado deve ser true para participacoes", async function () {
            const { registry, validator } = await loadFixture(deployRegistryFixture);
            const offchainId = toBytes32(PARTICIPACAO_UUID);
            
            await registry.connect(validator).registerParticipacao(
                offchainId, PARTICIPACAO_HASH, METADATA_HASH, ActionType.PRAIA
            );

            const proof = await registry.getProof(offchainId);
            expect(proof.photoAfterHash).to.equal(PARTICIPACAO_HASH);
            expect(proof.photoBeforeHash).to.equal(ethers.ZeroHash);
            expect(proof.metadataHash).to.equal(METADATA_HASH);
            expect(proof.validador).to.equal(validator.address);
            expect(proof.aiScore).to.equal(0n);
            expect(proof.aprovado).to.be.true;
        });
    });

    describe("verifyPhoto", function () {
        it("deve validar corretamente hashes apos o registro", async function () {
            const { registry, validator } = await loadFixture(deployRegistryFixture);
            const offchainId = toBytes32(LIMPEZA_UUID);
            
            await registry.connect(validator).registerLimpeza(
                offchainId, PHOTO_AFTER_HASH, PHOTO_BEFORE_HASH, METADATA_HASH,
                87n, ActionType.PRAIA, true
            );

            expect(await registry.verifyPhoto(offchainId, PHOTO_AFTER_HASH)).to.be.true;
            expect(await registry.verifyPhoto(offchainId, PHOTO_BEFORE_HASH)).to.be.true;
            
            const wrongHash = ethers.keccak256(ethers.toUtf8Bytes("foto-adulterada"));
            expect(await registry.verifyPhoto(offchainId, wrongHash)).to.be.false;
            expect(await registry.verifyPhoto(toBytes32("uuid-inexistente"), PHOTO_AFTER_HASH)).to.be.false;
        });
    });

    describe("verifyMetadata", function () {
        it("deve validar metadataHash corretamente", async function () {
            const { registry, validator } = await loadFixture(deployRegistryFixture);
            const offchainId = toBytes32(LIMPEZA_UUID);
            
            await registry.connect(validator).registerLimpeza(
                offchainId, PHOTO_AFTER_HASH, PHOTO_BEFORE_HASH, METADATA_HASH,
                87n, ActionType.PRAIA, true
            );

            expect(await registry.verifyMetadata(offchainId, METADATA_HASH)).to.be.true;
            
            const wrongMetadata = ethers.keccak256(ethers.toUtf8Bytes("wrong-metadata"));
            expect(await registry.verifyMetadata(offchainId, wrongMetadata)).to.be.false;
        });
    });

    describe("getProof", function () {
        it("deve reverter com ProofNotFound para offchainId inexistente", async function () {
            const { registry } = await loadFixture(deployRegistryFixture);
            const offchainId = toBytes32("inexistente");

            await expect(
                registry.getProof(offchainId)
            ).to.be.revertedWithCustomError(registry, "ProofNotFound").withArgs(offchainId);
        });
    });

    describe("Imutabilidade", function () {
        it("nao deve expor metodos de upgrade (UUPS)", async function () {
            const { registry } = await loadFixture(deployRegistryFixture);
            expect(typeof registry.upgradeToAndCall).to.equal("undefined");
        });
    });

describe("registerEducacao", function () {
        it("deve registrar acao educativa com metadataHash e emitir eventos", async function () {
            const { registry, validator } = await loadFixture(deployRegistryFixture);
            const offchainId = toBytes32("educacao-001");

            const tx = await registry.connect(validator).registerEducacao(
                offchainId, PHOTO_AFTER_HASH, METADATA_HASH, 45 // 45 pessoas impactadas
            );

            await expect(tx)
                .to.emit(registry, "EducacaoRegistered")
                .withArgs(offchainId, 45);

            await expect(tx)
                .to.emit(registry, "ProofRegistered")
                .withArgs(offchainId, PHOTO_AFTER_HASH, validator.address, true, ActionType.EDUCACAO, 0);

            const proof = await registry.getProof(offchainId);
            expect(proof.impactCount).to.equal(45n);
            expect(proof.metadataHash).to.equal(METADATA_HASH);
            expect(proof.actionType).to.equal(ActionType.EDUCACAO);
        });
    });

    describe("registerAdocaoCheckIn (Maquina de Estados)", function () {
        it("deve completar o ciclo de 3 meses de adocao estritamente na ordem", async function () {
            const { registry, validator } = await loadFixture(deployRegistryFixture);
            const adoptionId = toBytes32("adocao-001");
            const hashMes0 = toBytes32("foto-mes-0");
            const hashMes1 = toBytes32("foto-mes-1");
            const hashMes2 = toBytes32("foto-mes-2");
            const hashMes3 = toBytes32("foto-mes-3");

            // Mês 0 (Início)
            await expect(registry.connect(validator).registerAdocaoCheckIn(adoptionId, 0, hashMes0))
                .to.emit(registry, "AdocaoCheckInRegistered").withArgs(adoptionId, 0, hashMes0);
            
            // Tentativa de pular o Mês 1 e ir direto para o 2 (Deve falhar)
            await expect(
                registry.connect(validator).registerAdocaoCheckIn(adoptionId, 2, hashMes2)
            ).to.be.revertedWithCustomError(registry, "InvalidCheckInMonth").withArgs(1, 2);

            // Mês 1 e 2
            await registry.connect(validator).registerAdocaoCheckIn(adoptionId, 1, hashMes1);
            await registry.connect(validator).registerAdocaoCheckIn(adoptionId, 2, hashMes2);
            
            // Mês 3 (Conclusão)
            await registry.connect(validator).registerAdocaoCheckIn(adoptionId, 3, hashMes3);

            // Tentativa de registrar Mês 4 após concluído (Deve falhar)
            await expect(
                registry.connect(validator).registerAdocaoCheckIn(adoptionId, 4, toBytes32("foto-mes-4"))
            ).to.be.revertedWithCustomError(registry, "AdoptionAlreadyCompleted").withArgs(adoptionId);

            // Validação final do Storage
            const adoption = await registry.getAdoption(adoptionId);
            expect(adoption.checkInsCompleted).to.equal(3);
            expect(adoption.photoHashes[3]).to.equal(hashMes3);
        });
    });
});