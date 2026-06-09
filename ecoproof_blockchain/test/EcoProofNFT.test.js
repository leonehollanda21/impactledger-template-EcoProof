const { expect } = require("chai");
const { ethers, upgrades } = require("hardhat");
const { loadFixture } = require("@nomicfoundation/hardhat-network-helpers");

function toBytes32(str) {
    return ethers.keccak256(ethers.toUtf8Bytes(str));
}

function toAiScore(floatScore) {
    return Math.round(floatScore * 100);
}

describe("EcoProofNFT (Soulbound — EIP-5192)", function () {
    const LIMPEZA_UUID_1 = "550e8400-e29b-41d4-a716-446655440001";
    const EVENTO_UUID_1 = "550e8400-e29b-41d4-a716-446655440003";
    const METADATA_URI = "https://api.ecoproof.io/api/v1/nfts/1/metadata.json";

    const ActionType = { LIXO_RUA: 0, PRAIA: 1, CORREGO: 2, QUEIMADA: 3, OUTRO: 4, EDUCACAO: 5, ADOCAO: 6 };
    const EIP5192_INTERFACE_ID = "0xb45a3c0e";

    async function deployNFTFixture() {
        const [admin, minter, citizen1, citizen2, institute, stranger] = await ethers.getSigners();

        const NFT = await ethers.getContractFactory("EcoProofNFT");
        const nft = await upgrades.deployProxy(
            NFT,
            [admin.address, minter.address],
            { initializer: "initialize", kind: "uups" }
        );
        await nft.waitForDeployment();

        return { nft, admin, minter, citizen1, citizen2, institute, stranger };
    }

    describe("Deploy e Inicializacao", function () {
        it("deve configurar nome e simbolo como EcoProof Individual (ECOI)", async function () {
            const { nft } = await loadFixture(deployNFTFixture);
            expect(await nft.name()).to.equal("EcoProof Individual");
            expect(await nft.symbol()).to.equal("ECOI");
        });

        it("deve atribuir roles iniciais corretamente incluindo PAUSER", async function () {
            const { nft, admin, minter } = await loadFixture(deployNFTFixture);
            
            const MINTER_ROLE = await nft.MINTER_ROLE();
            const UPGRADER_ROLE = await nft.UPGRADER_ROLE();
            const PAUSER_ROLE = await nft.PAUSER_ROLE();
            const ADMIN_ROLE = await nft.DEFAULT_ADMIN_ROLE();

            expect(await nft.hasRole(MINTER_ROLE, minter.address)).to.be.true;
            expect(await nft.hasRole(UPGRADER_ROLE, admin.address)).to.be.true;
            expect(await nft.hasRole(PAUSER_ROLE, admin.address)).to.be.true;
            expect(await nft.hasRole(ADMIN_ROLE, admin.address)).to.be.true;
        });

        it("deve suportar EIP-5192 (Soulbound interface)", async function () {
            const { nft } = await loadFixture(deployNFTFixture);
            expect(await nft.supportsInterface(EIP5192_INTERFACE_ID)).to.be.true;
        });
    });

    describe("Soulbound (EIP-5192)", function () {
        it("deve emitir evento Locked ao mintar", async function () {
            const { nft, minter, citizen1 } = await loadFixture(deployNFTFixture);
            const offchainId = toBytes32(LIMPEZA_UUID_1);

            await expect(
                nft.connect(minter).mintLimpeza(
                    citizen1.address, METADATA_URI, offchainId, ActionType.PRAIA, 87
                )
            ).to.emit(nft, "Locked").withArgs(1n);
        });

        it("locked() deve retornar true para todo token mintado", async function () {
            const { nft, minter, citizen1 } = await loadFixture(deployNFTFixture);
            const offchainId = toBytes32(LIMPEZA_UUID_1);

            await nft.connect(minter).mintLimpeza(
                citizen1.address, METADATA_URI, offchainId, ActionType.PRAIA, 87
            );

            expect(await nft.locked(1n)).to.be.true;
        });

        it("deve BLOQUEAR transferência via transferFrom", async function () {
            const { nft, minter, citizen1, citizen2 } = await loadFixture(deployNFTFixture);
            const offchainId = toBytes32(LIMPEZA_UUID_1);

            await nft.connect(minter).mintLimpeza(
                citizen1.address, METADATA_URI, offchainId, ActionType.PRAIA, 87
            );

            await expect(
                nft.connect(citizen1).transferFrom(citizen1.address, citizen2.address, 1n)
            ).to.be.revertedWithCustomError(nft, "SoulboundNaoTransferivel");
        });

        it("deve BLOQUEAR transferência via safeTransferFrom", async function () {
            const { nft, minter, citizen1, citizen2 } = await loadFixture(deployNFTFixture);
            const offchainId = toBytes32(LIMPEZA_UUID_1);

            await nft.connect(minter).mintLimpeza(
                citizen1.address, METADATA_URI, offchainId, ActionType.PRAIA, 87
            );

            await expect(
                nft.connect(citizen1)["safeTransferFrom(address,address,uint256)"](
                    citizen1.address, citizen2.address, 1n
                )
            ).to.be.revertedWithCustomError(nft, "SoulboundNaoTransferivel");
        });

        it("locked() deve reverter para token inexistente", async function () {
            const { nft } = await loadFixture(deployNFTFixture);
            await expect(nft.locked(999n)).to.be.reverted;
        });
    });

    describe("mintLimpeza", function () {
        it("deve mintar NFT e emitir ActionMinted", async function () {
            const { nft, minter, citizen1 } = await loadFixture(deployNFTFixture);
            const offchainId = toBytes32(LIMPEZA_UUID_1);
            const aiScore = toAiScore(0.87);

            await expect(
                nft.connect(minter).mintLimpeza(
                    citizen1.address, METADATA_URI, offchainId, ActionType.PRAIA, aiScore
                )
            )
            .to.emit(nft, "ActionMinted")
            .withArgs(1n, citizen1.address, ActionType.PRAIA, 0, offchainId, aiScore);

            expect(await nft.ownerOf(1n)).to.equal(citizen1.address);
        });

        it("deve rejeitar re-mint do mesmo UUID garantindo idempotencia", async function () {
            const { nft, minter, citizen1 } = await loadFixture(deployNFTFixture);
            const offchainId = toBytes32(LIMPEZA_UUID_1);

            await nft.connect(minter).mintLimpeza(
                citizen1.address, METADATA_URI, offchainId, ActionType.PRAIA, 87
            );

            await expect(
                nft.connect(minter).mintLimpeza(
                    citizen1.address, METADATA_URI, offchainId, ActionType.PRAIA, 87
                )
            ).to.be.revertedWithCustomError(nft, "AlreadyMinted").withArgs(offchainId);
        });

        it("deve rejeitar mint sem a MINTER_ROLE", async function () {
            const { nft, stranger, citizen1 } = await loadFixture(deployNFTFixture);
            const offchainId = toBytes32(LIMPEZA_UUID_1);
            const MINTER_ROLE = await nft.MINTER_ROLE();

            await expect(
                nft.connect(stranger).mintLimpeza(
                    citizen1.address, METADATA_URI, offchainId, ActionType.PRAIA, 87
                )
            ).to.be.revertedWithCustomError(nft, "AccessControlUnauthorizedAccount")
             .withArgs(stranger.address, MINTER_ROLE);
        });

        it("deve rejeitar wallet zero", async function () {
            const { nft, minter } = await loadFixture(deployNFTFixture);
            
            await expect(
                nft.connect(minter).mintLimpeza(
                    ethers.ZeroAddress, METADATA_URI, toBytes32(LIMPEZA_UUID_1), ActionType.PRAIA, 87
                )
            ).to.be.revertedWithCustomError(nft, "ERC721InvalidReceiver")
             .withArgs(ethers.ZeroAddress);
        });
    });

    describe("Pausable", function () {
        it("deve rejeitar mint quando pausado", async function () {
            const { nft, admin, minter, citizen1 } = await loadFixture(deployNFTFixture);
            
            await nft.connect(admin).pause();

            await expect(
                nft.connect(minter).mintLimpeza(
                    citizen1.address, METADATA_URI, toBytes32(LIMPEZA_UUID_1), ActionType.PRAIA, 87
                )
            ).to.be.revertedWithCustomError(nft, "EnforcedPause");
        });

        it("deve permitir mint apos unpause", async function () {
            const { nft, admin, minter, citizen1 } = await loadFixture(deployNFTFixture);
            
            await nft.connect(admin).pause();
            await nft.connect(admin).unpause();

            await expect(
                nft.connect(minter).mintLimpeza(
                    citizen1.address, METADATA_URI, toBytes32(LIMPEZA_UUID_1), ActionType.PRAIA, 87
                )
            ).to.emit(nft, "ActionMinted");
        });

        it("deve rejeitar pause sem PAUSER_ROLE", async function () {
            const { nft, stranger } = await loadFixture(deployNFTFixture);
            
            await expect(
                nft.connect(stranger).pause()
            ).to.be.revertedWithCustomError(nft, "AccessControlUnauthorizedAccount");
        });
    });

    describe("mintBatch (Mutiroes)", function () {
        it("deve mintar NFTs em lote e emitir BatchMinted + Locked para cada", async function () {
            const { nft, minter, citizen1, citizen2, institute } = await loadFixture(deployNFTFixture);
            const eventHash = toBytes32(EVENTO_UUID_1);
            
            const params = [
                { to: citizen1.address, uri: METADATA_URI, offchainId: toBytes32("p-1"), actionType: ActionType.PRAIA, institutionWallet: institute.address },
                { to: citizen2.address, uri: METADATA_URI, offchainId: toBytes32("p-2"), actionType: ActionType.PRAIA, institutionWallet: institute.address },
            ];

            const tx = await nft.connect(minter).mintBatch(params, eventHash);
            
            // Deve emitir BatchMinted
            await expect(tx)
                .to.emit(nft, "BatchMinted")
                .withArgs(eventHash, institute.address, 2n);

            // Deve emitir Locked para cada token
            await expect(tx).to.emit(nft, "Locked").withArgs(1n);
            await expect(tx).to.emit(nft, "Locked").withArgs(2n);

            expect(await nft.totalSupply()).to.equal(2n);

            // Ambos são Soulbound
            expect(await nft.locked(1n)).to.be.true;
            expect(await nft.locked(2n)).to.be.true;
        });

        it("deve rejeitar lote vazio", async function () {
            const { nft, minter } = await loadFixture(deployNFTFixture);
            await expect(
                nft.connect(minter).mintBatch([], toBytes32(EVENTO_UUID_1))
            ).to.be.revertedWithCustomError(nft, "EmptyBatch");
        });

        it("deve rejeitar lote acima de 500 itens", async function () {
            const { nft, minter, citizen1, institute } = await loadFixture(deployNFTFixture);
            
            const params = Array.from({ length: 501 }, (_, i) => ({
                to: citizen1.address,
                uri: METADATA_URI,
                offchainId: toBytes32(`p-${i}`),
                actionType: ActionType.PRAIA,
                institutionWallet: institute.address,
            }));

            await expect(
                nft.connect(minter).mintBatch(params, toBytes32(EVENTO_UUID_1))
            ).to.be.revertedWithCustomError(nft, "InvalidBatchSize");
        });
    });

    describe("mintGuardiao (Soulbound)", function () {
        it("deve mintar NFT de guardiao para adocao concluida e emitir Locked", async function () {
            const { nft, minter, citizen1 } = await loadFixture(deployNFTFixture);
            const adoptionId = toBytes32("adocao-001");

            const tx = await nft.connect(minter).mintGuardiao(
                citizen1.address, METADATA_URI, adoptionId
            );

            await expect(tx)
                .to.emit(nft, "GuardiaoMinted")
                .withArgs(1n, citizen1.address, adoptionId);

            // EIP-5192: Garantir que o token nasceu bloqueado
            await expect(tx).to.emit(nft, "Locked").withArgs(1n);

            const record = await nft.getRecord(1n);
            expect(record.actionType).to.equal(ActionType.ADOCAO);
            expect(record.offchainId).to.equal(adoptionId);
            expect(await nft.locked(1n)).to.be.true;
        });
    });
});