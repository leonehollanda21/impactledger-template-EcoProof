const { expect } = require("chai");
const { ethers, upgrades } = require("hardhat");
const { loadFixture } = require("@nomicfoundation/hardhat-network-helpers");

function toBytes32(str) {
    return ethers.keccak256(ethers.toUtf8Bytes(str));
}

describe("DenunciaNFT (Soulbound ECFD — Denúncia Ambiental Verificada)", function () {
    const METADATA_URI = "https://api.ecoproof.io/api/v1/nfts/denuncia/metadata.json";
    const EIP5192_INTERFACE_ID = "0xb45a3c0e";
    const PHOTO_BEFORE = toBytes32("photo-before-123");
    const PHOTO_AFTER = toBytes32("photo-after-123");
    const DESCRIPTION = "Descarte ilegal de lixo na margem do rio";

    async function deployDenunciaFixture() {
        const [admin, minter, citizen1, citizen2, stranger] = await ethers.getSigners();

        const DenunciaNFT = await ethers.getContractFactory("DenunciaNFT");
        const nft = await upgrades.deployProxy(
            DenunciaNFT,
            [admin.address, minter.address],
            { initializer: "initialize", kind: "uups" }
        );
        await nft.waitForDeployment();

        return { nft, admin, minter, citizen1, citizen2, stranger };
    }

    describe("Deploy e Inicializacao", function () {
        it("deve configurar nome e simbolo como EcoProof Denuncia (ECFD)", async function () {
            const { nft } = await loadFixture(deployDenunciaFixture);
            expect(await nft.name()).to.equal("EcoProof Denuncia");
            expect(await nft.symbol()).to.equal("ECFD");
        });

        it("deve atribuir roles iniciais corretamente", async function () {
            const { nft, admin, minter } = await loadFixture(deployDenunciaFixture);
            
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
            const { nft } = await loadFixture(deployDenunciaFixture);
            expect(await nft.supportsInterface(EIP5192_INTERFACE_ID)).to.be.true;
        });

        it("totalReported e totalResolved devem comecar em 0", async function () {
            const { nft } = await loadFixture(deployDenunciaFixture);
            expect(await nft.totalReported()).to.equal(0n);
            expect(await nft.totalResolved()).to.equal(0n);
        });
    });

    describe("registrarDenuncia", function () {
        it("deve registrar a denuncia com sucesso e emitir DenunciaRegistrada", async function () {
            const { nft, minter, citizen1 } = await loadFixture(deployDenunciaFixture);
            const offchainId = toBytes32("denuncia-001");

            const tx = await nft.connect(minter).registrarDenuncia(
                citizen1.address, offchainId, PHOTO_BEFORE, DESCRIPTION
            );

            await expect(tx)
                .to.emit(nft, "DenunciaRegistrada")
                .withArgs(offchainId, citizen1.address, PHOTO_BEFORE, DESCRIPTION);

            expect(await nft.isRegistered(offchainId)).to.be.true;
            expect(await nft.totalReported()).to.equal(1n);
        });

        it("deve armazenar os dados do record corretamente", async function () {
            const { nft, minter, citizen1 } = await loadFixture(deployDenunciaFixture);
            const offchainId = toBytes32("denuncia-001");

            await nft.connect(minter).registrarDenuncia(
                citizen1.address, offchainId, PHOTO_BEFORE, DESCRIPTION
            );

            const record = await nft.getDenuncia(offchainId);
            expect(record.citizen).to.equal(citizen1.address);
            expect(record.offchainId).to.equal(offchainId);
            expect(record.photoBeforeHash).to.equal(PHOTO_BEFORE);
            expect(record.photoAfterHash).to.equal(ethers.ZeroHash);
            expect(record.description).to.equal(DESCRIPTION);
            expect(record.status).to.equal(0); // Status.REPORTADA
            expect(record.reportedAt).to.be.greaterThan(0n);
            expect(record.resolvedAt).to.equal(0n);
            expect(record.tokenId).to.equal(0n);
        });

        it("deve rejeitar registro duplicado da mesma denuncia (idempotencia)", async function () {
            const { nft, minter, citizen1 } = await loadFixture(deployDenunciaFixture);
            const offchainId = toBytes32("denuncia-001");

            await nft.connect(minter).registrarDenuncia(
                citizen1.address, offchainId, PHOTO_BEFORE, DESCRIPTION
            );

            await expect(
                nft.connect(minter).registrarDenuncia(
                    citizen1.address, offchainId, PHOTO_BEFORE, DESCRIPTION
                )
            ).to.be.revertedWithCustomError(nft, "AlreadyRegistered").withArgs(offchainId);
        });

        it("deve rejeitar chamada sem MINTER_ROLE", async function () {
            const { nft, stranger, citizen1 } = await loadFixture(deployDenunciaFixture);
            const offchainId = toBytes32("denuncia-001");
            const MINTER_ROLE = await nft.MINTER_ROLE();

            await expect(
                nft.connect(stranger).registrarDenuncia(
                    citizen1.address, offchainId, PHOTO_BEFORE, DESCRIPTION
                )
            ).to.be.revertedWithCustomError(nft, "AccessControlUnauthorizedAccount")
             .withArgs(stranger.address, MINTER_ROLE);
        });

        it("deve rejeitar com dados invalidos", async function () {
            const { nft, minter, citizen1 } = await loadFixture(deployDenunciaFixture);
            const offchainId = toBytes32("denuncia-001");

            // Cidadão wallet zero
            await expect(
                nft.connect(minter).registrarDenuncia(
                    ethers.ZeroAddress, offchainId, PHOTO_BEFORE, DESCRIPTION
                )
            ).to.be.revertedWithCustomError(nft, "InvalidAddress");

            // offchainId zero
            await expect(
                nft.connect(minter).registrarDenuncia(
                    citizen1.address, ethers.ZeroHash, PHOTO_BEFORE, DESCRIPTION
                )
            ).to.be.revertedWithCustomError(nft, "InvalidHash");

            // photoBeforeHash zero
            await expect(
                nft.connect(minter).registrarDenuncia(
                    citizen1.address, offchainId, ethers.ZeroHash, DESCRIPTION
                )
            ).to.be.revertedWithCustomError(nft, "InvalidHash");

            // descrição vazia
            await expect(
                nft.connect(minter).registrarDenuncia(
                    citizen1.address, offchainId, PHOTO_BEFORE, ""
                )
            ).to.be.revertedWithCustomError(nft, "InvalidDescription");
        });
    });

    describe("resolverDenuncia e Mint", function () {
        it("deve resolver a denuncia com sucesso, mintar o NFT e emitir DenunciaResolvida + Locked", async function () {
            const { nft, minter, citizen1 } = await loadFixture(deployDenunciaFixture);
            const offchainId = toBytes32("denuncia-001");

            await nft.connect(minter).registrarDenuncia(
                citizen1.address, offchainId, PHOTO_BEFORE, DESCRIPTION
            );

            const tx = await nft.connect(minter).resolverDenuncia(
                offchainId, PHOTO_AFTER, METADATA_URI
            );

            await expect(tx)
                .to.emit(nft, "DenunciaResolvida")
                .withArgs(offchainId, 1n, PHOTO_AFTER);

            await expect(tx)
                .to.emit(nft, "Locked")
                .withArgs(1n);

            expect(await nft.ownerOf(1n)).to.equal(citizen1.address);
            expect(await nft.tokenURI(1n)).to.equal(METADATA_URI);

            const record = await nft.getDenuncia(offchainId);
            expect(record.status).to.equal(1); // Status.RESOLVIDA
            expect(record.photoAfterHash).to.equal(PHOTO_AFTER);
            expect(record.resolvedAt).to.be.greaterThan(0n);
            expect(record.tokenId).to.equal(1n);

            expect(await nft.totalResolved()).to.equal(1n);
            expect(await nft.totalSupply()).to.equal(1n);
        });

        it("deve rejeitar resolver denuncia nao registrada", async function () {
            const { nft, minter } = await loadFixture(deployDenunciaFixture);
            const offchainId = toBytes32("denuncia-inexistente");

            await expect(
                nft.connect(minter).resolverDenuncia(
                    offchainId, PHOTO_AFTER, METADATA_URI
                )
            ).to.be.revertedWithCustomError(nft, "DenunciaNotRegistered").withArgs(offchainId);
        });

        it("deve rejeitar resolver denuncia ja resolvida", async function () {
            const { nft, minter, citizen1 } = await loadFixture(deployDenunciaFixture);
            const offchainId = toBytes32("denuncia-001");

            await nft.connect(minter).registrarDenuncia(
                citizen1.address, offchainId, PHOTO_BEFORE, DESCRIPTION
            );

            await nft.connect(minter).resolverDenuncia(
                offchainId, PHOTO_AFTER, METADATA_URI
            );

            await expect(
                nft.connect(minter).resolverDenuncia(
                    offchainId, PHOTO_AFTER, METADATA_URI
                )
            ).to.be.revertedWithCustomError(nft, "DenunciaAlreadyResolved").withArgs(offchainId);
        });

        it("deve rejeitar chamada sem MINTER_ROLE", async function () {
            const { nft, minter, citizen1, stranger } = await loadFixture(deployDenunciaFixture);
            const offchainId = toBytes32("denuncia-001");
            const MINTER_ROLE = await nft.MINTER_ROLE();

            await nft.connect(minter).registrarDenuncia(
                citizen1.address, offchainId, PHOTO_BEFORE, DESCRIPTION
            );

            await expect(
                nft.connect(stranger).resolverDenuncia(
                    offchainId, PHOTO_AFTER, METADATA_URI
                )
            ).to.be.revertedWithCustomError(nft, "AccessControlUnauthorizedAccount")
             .withArgs(stranger.address, MINTER_ROLE);
        });

        it("deve rejeitar com parametros de resolucao invalidos", async function () {
            const { nft, minter, citizen1 } = await loadFixture(deployDenunciaFixture);
            const offchainId = toBytes32("denuncia-001");

            await nft.connect(minter).registrarDenuncia(
                citizen1.address, offchainId, PHOTO_BEFORE, DESCRIPTION
            );

            // photoAfterHash zero
            await expect(
                nft.connect(minter).resolverDenuncia(
                    offchainId, ethers.ZeroHash, METADATA_URI
                )
            ).to.be.revertedWithCustomError(nft, "InvalidHash");

            // uri vazia
            await expect(
                nft.connect(minter).resolverDenuncia(
                    offchainId, PHOTO_AFTER, ""
                )
            ).to.be.revertedWithCustomError(nft, "InvalidURI");
        });
    });

    describe("Soulbound (EIP-5192)", function () {
        it("locked() deve retornar true para todo token mintado", async function () {
            const { nft, minter, citizen1 } = await loadFixture(deployDenunciaFixture);
            const offchainId = toBytes32("denuncia-001");

            await nft.connect(minter).registrarDenuncia(
                citizen1.address, offchainId, PHOTO_BEFORE, DESCRIPTION
            );
            await nft.connect(minter).resolverDenuncia(
                offchainId, PHOTO_AFTER, METADATA_URI
            );

            expect(await nft.locked(1n)).to.be.true;
        });

        it("deve BLOQUEAR transferencia via transferFrom", async function () {
            const { nft, minter, citizen1, citizen2 } = await loadFixture(deployDenunciaFixture);
            const offchainId = toBytes32("denuncia-001");

            await nft.connect(minter).registrarDenuncia(
                citizen1.address, offchainId, PHOTO_BEFORE, DESCRIPTION
            );
            await nft.connect(minter).resolverDenuncia(
                offchainId, PHOTO_AFTER, METADATA_URI
            );

            await expect(
                nft.connect(citizen1).transferFrom(citizen1.address, citizen2.address, 1n)
            ).to.be.revertedWithCustomError(nft, "SoulboundNaoTransferivel");
        });

        it("deve BLOQUEAR transferencia via safeTransferFrom", async function () {
            const { nft, minter, citizen1, citizen2 } = await loadFixture(deployDenunciaFixture);
            const offchainId = toBytes32("denuncia-001");

            await nft.connect(minter).registrarDenuncia(
                citizen1.address, offchainId, PHOTO_BEFORE, DESCRIPTION
            );
            await nft.connect(minter).resolverDenuncia(
                offchainId, PHOTO_AFTER, METADATA_URI
            );

            await expect(
                nft.connect(citizen1)["safeTransferFrom(address,address,uint256)"](
                    citizen1.address, citizen2.address, 1n
                )
            ).to.be.revertedWithCustomError(nft, "SoulboundNaoTransferivel");
        });

        it("locked() deve reverter para token inexistente", async function () {
            const { nft } = await loadFixture(deployDenunciaFixture);
            await expect(nft.locked(999n)).to.be.reverted;
        });
    });

    describe("Pausable", function () {
        it("deve rejeitar registrarDenuncia quando pausado", async function () {
            const { nft, admin, minter, citizen1 } = await loadFixture(deployDenunciaFixture);
            const offchainId = toBytes32("denuncia-paused");

            await nft.connect(admin).pause();

            await expect(
                nft.connect(minter).registrarDenuncia(
                    citizen1.address, offchainId, PHOTO_BEFORE, DESCRIPTION
                )
            ).to.be.revertedWithCustomError(nft, "EnforcedPause");
        });

        it("deve rejeitar resolverDenuncia quando pausado", async function () {
            const { nft, admin, minter, citizen1 } = await loadFixture(deployDenunciaFixture);
            const offchainId = toBytes32("denuncia-001");

            await nft.connect(minter).registrarDenuncia(
                citizen1.address, offchainId, PHOTO_BEFORE, DESCRIPTION
            );

            await nft.connect(admin).pause();

            await expect(
                nft.connect(minter).resolverDenuncia(
                    offchainId, PHOTO_AFTER, METADATA_URI
                )
            ).to.be.revertedWithCustomError(nft, "EnforcedPause");
        });

        it("deve permitir acoes apos unpause", async function () {
            const { nft, admin, minter, citizen1 } = await loadFixture(deployDenunciaFixture);
            const offchainId = toBytes32("denuncia-unpaused");

            await nft.connect(admin).pause();
            await nft.connect(admin).unpause();

            await expect(
                nft.connect(minter).registrarDenuncia(
                    citizen1.address, offchainId, PHOTO_BEFORE, DESCRIPTION
                )
            ).to.emit(nft, "DenunciaRegistrada");
        });

        it("deve rejeitar pause sem PAUSER_ROLE", async function () {
            const { nft, stranger } = await loadFixture(deployDenunciaFixture);
            
            await expect(
                nft.connect(stranger).pause()
            ).to.be.revertedWithCustomError(nft, "AccessControlUnauthorizedAccount");
        });
    });
});
