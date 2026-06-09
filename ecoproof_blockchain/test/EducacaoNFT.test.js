const { expect } = require("chai");
const { ethers, upgrades } = require("hardhat");
const { loadFixture } = require("@nomicfoundation/hardhat-network-helpers");

function toBytes32(str) {
    return ethers.keccak256(ethers.toUtf8Bytes(str));
}

describe("EducacaoNFT (Soulbound ECED — Educação Ambiental)", function () {
    const METADATA_URI = "https://api.ecoproof.io/api/v1/nfts/educacao/metadata.json";
    const EducacaoType = { PALESTRA: 0, OFICINA: 1, RODA_CONVERSA: 2, MUTIRAO_EDUCATIVO: 3, OUTRO: 4 };
    const IssuedBy = { ADMIN: 0, INSTITUTO: 1 };
    const EIP5192_INTERFACE_ID = "0xb45a3c0e";

    async function deployEducacaoFixture() {
        const [admin, minter, citizen1, citizen2, institute, stranger] = await ethers.getSigners();

        const EducacaoNFT = await ethers.getContractFactory("EducacaoNFT");
        const nft = await upgrades.deployProxy(
            EducacaoNFT,
            [admin.address, minter.address],
            { initializer: "initialize", kind: "uups" }
        );
        await nft.waitForDeployment();

        return { nft, admin, minter, citizen1, citizen2, institute, stranger };
    }

    describe("Deploy e Inicializacao", function () {
        it("deve configurar nome e simbolo como EcoProof Educacao (ECED)", async function () {
            const { nft } = await loadFixture(deployEducacaoFixture);
            expect(await nft.name()).to.equal("EcoProof Educacao");
            expect(await nft.symbol()).to.equal("ECED");
        });

        it("deve atribuir roles iniciais corretamente", async function () {
            const { nft, admin, minter } = await loadFixture(deployEducacaoFixture);
            
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
            const { nft } = await loadFixture(deployEducacaoFixture);
            expect(await nft.supportsInterface(EIP5192_INTERFACE_ID)).to.be.true;
        });

        it("totalPeopleImpacted deve comecar em 0", async function () {
            const { nft } = await loadFixture(deployEducacaoFixture);
            expect(await nft.totalPeopleImpacted()).to.equal(0n);
        });
    });

    describe("Soulbound (EIP-5192)", function () {
        it("deve emitir evento Locked ao mintar", async function () {
            const { nft, minter, citizen1, institute } = await loadFixture(deployEducacaoFixture);
            const offchainId = toBytes32("educacao-001");

            await expect(
                nft.connect(minter).mintEducacao(
                    citizen1.address, METADATA_URI, offchainId,
                    EducacaoType.PALESTRA, institute.address, 45,
                    IssuedBy.INSTITUTO
                )
            ).to.emit(nft, "Locked").withArgs(1n);
        });

        it("locked() deve retornar true para todo token mintado", async function () {
            const { nft, minter, citizen1, institute } = await loadFixture(deployEducacaoFixture);
            const offchainId = toBytes32("educacao-001");

            await nft.connect(minter).mintEducacao(
                citizen1.address, METADATA_URI, offchainId,
                EducacaoType.PALESTRA, institute.address, 45,
                IssuedBy.INSTITUTO
            );

            expect(await nft.locked(1n)).to.be.true;
        });

        it("deve BLOQUEAR transferencia via transferFrom", async function () {
            const { nft, minter, citizen1, citizen2, institute } = await loadFixture(deployEducacaoFixture);
            const offchainId = toBytes32("educacao-001");

            await nft.connect(minter).mintEducacao(
                citizen1.address, METADATA_URI, offchainId,
                EducacaoType.PALESTRA, institute.address, 45,
                IssuedBy.INSTITUTO
            );

            await expect(
                nft.connect(citizen1).transferFrom(citizen1.address, citizen2.address, 1n)
            ).to.be.revertedWithCustomError(nft, "SoulboundNaoTransferivel");
        });

        it("deve BLOQUEAR transferencia via safeTransferFrom", async function () {
            const { nft, minter, citizen1, citizen2, institute } = await loadFixture(deployEducacaoFixture);
            const offchainId = toBytes32("educacao-001");

            await nft.connect(minter).mintEducacao(
                citizen1.address, METADATA_URI, offchainId,
                EducacaoType.PALESTRA, institute.address, 45,
                IssuedBy.INSTITUTO
            );

            await expect(
                nft.connect(citizen1)["safeTransferFrom(address,address,uint256)"](
                    citizen1.address, citizen2.address, 1n
                )
            ).to.be.revertedWithCustomError(nft, "SoulboundNaoTransferivel");
        });

        it("locked() deve reverter para token inexistente", async function () {
            const { nft } = await loadFixture(deployEducacaoFixture);
            await expect(nft.locked(999n)).to.be.reverted;
        });
    });

    describe("mintEducacao", function () {
        it("deve mintar NFT de educacao e emitir EducacaoMinted com impactCount", async function () {
            const { nft, minter, citizen1, institute } = await loadFixture(deployEducacaoFixture);
            const offchainId = toBytes32("educacao-palestra-001");

            const tx = await nft.connect(minter).mintEducacao(
                citizen1.address, METADATA_URI, offchainId,
                EducacaoType.PALESTRA, institute.address, 45,
                IssuedBy.INSTITUTO
            );

            await expect(tx)
                .to.emit(nft, "EducacaoMinted")
                .withArgs(1n, citizen1.address, EducacaoType.PALESTRA, IssuedBy.INSTITUTO, offchainId, 45);

            await expect(tx).to.emit(nft, "Locked").withArgs(1n);

            expect(await nft.ownerOf(1n)).to.equal(citizen1.address);
        });

        it("deve armazenar o record completo com todos os campos", async function () {
            const { nft, minter, citizen1, institute } = await loadFixture(deployEducacaoFixture);
            const offchainId = toBytes32("educacao-palestra-001");

            await nft.connect(minter).mintEducacao(
                citizen1.address, METADATA_URI, offchainId,
                EducacaoType.PALESTRA, institute.address, 45,
                IssuedBy.INSTITUTO
            );

            const record = await nft.getRecord(1n);
            expect(record.citizen).to.equal(citizen1.address);
            expect(record.educacaoType).to.equal(EducacaoType.PALESTRA);
            expect(record.issuedBy).to.equal(IssuedBy.INSTITUTO);
            expect(record.validatorWallet).to.equal(institute.address);
            expect(record.impactCount).to.equal(45n);
            expect(record.offchainId).to.equal(offchainId);
            expect(record.issuedAt).to.be.greaterThan(0n);
        });

        it("deve aceitar mint validado pelo admin (IssuedBy.ADMIN)", async function () {
            const { nft, minter, citizen1, admin } = await loadFixture(deployEducacaoFixture);
            const offchainId = toBytes32("educacao-cidadao-001");

            const tx = await nft.connect(minter).mintEducacao(
                citizen1.address, METADATA_URI, offchainId,
                EducacaoType.RODA_CONVERSA, admin.address, 20,
                IssuedBy.ADMIN
            );

            await expect(tx)
                .to.emit(nft, "EducacaoMinted")
                .withArgs(1n, citizen1.address, EducacaoType.RODA_CONVERSA, IssuedBy.ADMIN, offchainId, 20);

            const record = await nft.getRecord(1n);
            expect(record.issuedBy).to.equal(IssuedBy.ADMIN);
        });

        it("deve atualizar totalPeopleImpacted a cada mint", async function () {
            const { nft, minter, citizen1, citizen2, institute } = await loadFixture(deployEducacaoFixture);

            await nft.connect(minter).mintEducacao(
                citizen1.address, METADATA_URI, toBytes32("edu-1"),
                EducacaoType.PALESTRA, institute.address, 45,
                IssuedBy.INSTITUTO
            );

            expect(await nft.totalPeopleImpacted()).to.equal(45n);

            await nft.connect(minter).mintEducacao(
                citizen2.address, METADATA_URI, toBytes32("edu-2"),
                EducacaoType.OFICINA, institute.address, 30,
                IssuedBy.INSTITUTO
            );

            expect(await nft.totalPeopleImpacted()).to.equal(75n);
        });

        it("deve suportar todos os tipos de acao educativa", async function () {
            const { nft, minter, citizen1, institute } = await loadFixture(deployEducacaoFixture);

            const types = [
                { type: EducacaoType.PALESTRA, label: "palestra" },
                { type: EducacaoType.OFICINA, label: "oficina" },
                { type: EducacaoType.RODA_CONVERSA, label: "roda" },
                { type: EducacaoType.MUTIRAO_EDUCATIVO, label: "mutirao" },
                { type: EducacaoType.OUTRO, label: "outro" },
            ];

            for (let i = 0; i < types.length; i++) {
                const offchainId = toBytes32(`edu-type-${types[i].label}`);
                await nft.connect(minter).mintEducacao(
                    citizen1.address, METADATA_URI, offchainId,
                    types[i].type, institute.address, 10,
                    IssuedBy.INSTITUTO
                );

                const record = await nft.getRecord(i + 1);
                expect(record.educacaoType).to.equal(types[i].type);
            }
        });

        it("deve rejeitar re-mint do mesmo offchainId (idempotencia)", async function () {
            const { nft, minter, citizen1, institute } = await loadFixture(deployEducacaoFixture);
            const offchainId = toBytes32("educacao-001");

            await nft.connect(minter).mintEducacao(
                citizen1.address, METADATA_URI, offchainId,
                EducacaoType.PALESTRA, institute.address, 45,
                IssuedBy.INSTITUTO
            );

            await expect(
                nft.connect(minter).mintEducacao(
                    citizen1.address, METADATA_URI, offchainId,
                    EducacaoType.PALESTRA, institute.address, 45,
                    IssuedBy.INSTITUTO
                )
            ).to.be.revertedWithCustomError(nft, "AlreadyMinted").withArgs(offchainId);
        });

        it("deve rejeitar impactCount zero", async function () {
            const { nft, minter, citizen1, institute } = await loadFixture(deployEducacaoFixture);
            const offchainId = toBytes32("educacao-zero");

            await expect(
                nft.connect(minter).mintEducacao(
                    citizen1.address, METADATA_URI, offchainId,
                    EducacaoType.PALESTRA, institute.address, 0,
                    IssuedBy.INSTITUTO
                )
            ).to.be.revertedWithCustomError(nft, "InvalidImpactCount");
        });

        it("deve rejeitar mint sem MINTER_ROLE", async function () {
            const { nft, stranger, citizen1, institute } = await loadFixture(deployEducacaoFixture);
            const MINTER_ROLE = await nft.MINTER_ROLE();

            await expect(
                nft.connect(stranger).mintEducacao(
                    citizen1.address, METADATA_URI, toBytes32("edu-x"),
                    EducacaoType.PALESTRA, institute.address, 45,
                    IssuedBy.INSTITUTO
                )
            ).to.be.revertedWithCustomError(nft, "AccessControlUnauthorizedAccount")
             .withArgs(stranger.address, MINTER_ROLE);
        });

        it("deve rejeitar wallet zero", async function () {
            const { nft, minter, institute } = await loadFixture(deployEducacaoFixture);

            await expect(
                nft.connect(minter).mintEducacao(
                    ethers.ZeroAddress, METADATA_URI, toBytes32("edu-zero-wallet"),
                    EducacaoType.PALESTRA, institute.address, 45,
                    IssuedBy.INSTITUTO
                )
            ).to.be.revertedWithCustomError(nft, "ERC721InvalidReceiver")
             .withArgs(ethers.ZeroAddress);
        });
    });

    describe("Pausable", function () {
        it("deve rejeitar mint quando pausado", async function () {
            const { nft, admin, minter, citizen1, institute } = await loadFixture(deployEducacaoFixture);
            
            await nft.connect(admin).pause();

            await expect(
                nft.connect(minter).mintEducacao(
                    citizen1.address, METADATA_URI, toBytes32("edu-paused"),
                    EducacaoType.PALESTRA, institute.address, 45,
                    IssuedBy.INSTITUTO
                )
            ).to.be.revertedWithCustomError(nft, "EnforcedPause");
        });

        it("deve permitir mint apos unpause", async function () {
            const { nft, admin, minter, citizen1, institute } = await loadFixture(deployEducacaoFixture);
            
            await nft.connect(admin).pause();
            await nft.connect(admin).unpause();

            await expect(
                nft.connect(minter).mintEducacao(
                    citizen1.address, METADATA_URI, toBytes32("edu-unpaused"),
                    EducacaoType.PALESTRA, institute.address, 45,
                    IssuedBy.INSTITUTO
                )
            ).to.emit(nft, "EducacaoMinted");
        });

        it("deve rejeitar pause sem PAUSER_ROLE", async function () {
            const { nft, stranger } = await loadFixture(deployEducacaoFixture);
            
            await expect(
                nft.connect(stranger).pause()
            ).to.be.revertedWithCustomError(nft, "AccessControlUnauthorizedAccount");
        });
    });

    describe("mintBatch (Educacao em lote)", function () {
        it("deve mintar NFTs em lote e emitir BatchEducacaoMinted com totalImpact", async function () {
            const { nft, minter, citizen1, citizen2, institute } = await loadFixture(deployEducacaoFixture);
            const eventHash = toBytes32("evento-educativo-001");

            const params = [
                {
                    to: citizen1.address, uri: METADATA_URI,
                    offchainId: toBytes32("batch-edu-1"),
                    educacaoType: EducacaoType.PALESTRA,
                    validatorWallet: institute.address,
                    impactCount: 45
                },
                {
                    to: citizen2.address, uri: METADATA_URI,
                    offchainId: toBytes32("batch-edu-2"),
                    educacaoType: EducacaoType.OFICINA,
                    validatorWallet: institute.address,
                    impactCount: 30
                },
            ];

            const tx = await nft.connect(minter).mintBatch(params, eventHash, IssuedBy.INSTITUTO);

            await expect(tx)
                .to.emit(nft, "BatchEducacaoMinted")
                .withArgs(eventHash, institute.address, 2n, 75n);

            // Cada token emite Locked
            await expect(tx).to.emit(nft, "Locked").withArgs(1n);
            await expect(tx).to.emit(nft, "Locked").withArgs(2n);

            expect(await nft.totalSupply()).to.equal(2n);
            expect(await nft.totalPeopleImpacted()).to.equal(75n);

            // Ambos são Soulbound
            expect(await nft.locked(1n)).to.be.true;
            expect(await nft.locked(2n)).to.be.true;
        });

        it("deve rejeitar lote vazio", async function () {
            const { nft, minter } = await loadFixture(deployEducacaoFixture);
            await expect(
                nft.connect(minter).mintBatch([], toBytes32("evt"), IssuedBy.INSTITUTO)
            ).to.be.revertedWithCustomError(nft, "EmptyBatch");
        });

        it("deve rejeitar lote acima de 500 itens", async function () {
            const { nft, minter, citizen1, institute } = await loadFixture(deployEducacaoFixture);

            const params = Array.from({ length: 501 }, (_, i) => ({
                to: citizen1.address,
                uri: METADATA_URI,
                offchainId: toBytes32(`batch-edu-${i}`),
                educacaoType: EducacaoType.PALESTRA,
                validatorWallet: institute.address,
                impactCount: 10,
            }));

            await expect(
                nft.connect(minter).mintBatch(params, toBytes32("evt-big"), IssuedBy.INSTITUTO)
            ).to.be.revertedWithCustomError(nft, "InvalidBatchSize");
        });

        it("deve pular entradas com impactCount zero no lote", async function () {
            const { nft, minter, citizen1, citizen2, institute } = await loadFixture(deployEducacaoFixture);
            const eventHash = toBytes32("evento-educativo-skip");

            const params = [
                {
                    to: citizen1.address, uri: METADATA_URI,
                    offchainId: toBytes32("batch-skip-1"),
                    educacaoType: EducacaoType.PALESTRA,
                    validatorWallet: institute.address,
                    impactCount: 45
                },
                {
                    to: citizen2.address, uri: METADATA_URI,
                    offchainId: toBytes32("batch-skip-2"),
                    educacaoType: EducacaoType.OFICINA,
                    validatorWallet: institute.address,
                    impactCount: 0 // Deve ser pulado
                },
            ];

            const tx = await nft.connect(minter).mintBatch(params, eventHash, IssuedBy.INSTITUTO);

            await expect(tx)
                .to.emit(nft, "BatchEducacaoMinted")
                .withArgs(eventHash, institute.address, 1n, 45n);

            expect(await nft.totalSupply()).to.equal(1n);
            expect(await nft.totalPeopleImpacted()).to.equal(45n);
        });
    });

    describe("Views", function () {
        it("totalSupply deve retornar contagem correta", async function () {
            const { nft, minter, citizen1, institute } = await loadFixture(deployEducacaoFixture);

            expect(await nft.totalSupply()).to.equal(0n);

            await nft.connect(minter).mintEducacao(
                citizen1.address, METADATA_URI, toBytes32("edu-supply-1"),
                EducacaoType.PALESTRA, institute.address, 10,
                IssuedBy.INSTITUTO
            );

            expect(await nft.totalSupply()).to.equal(1n);
        });

        it("isMinted deve retornar true para offchainId existente", async function () {
            const { nft, minter, citizen1, institute } = await loadFixture(deployEducacaoFixture);
            const offchainId = toBytes32("edu-minted-check");

            expect(await nft.isMinted(offchainId)).to.be.false;

            await nft.connect(minter).mintEducacao(
                citizen1.address, METADATA_URI, offchainId,
                EducacaoType.PALESTRA, institute.address, 10,
                IssuedBy.INSTITUTO
            );

            expect(await nft.isMinted(offchainId)).to.be.true;
        });

        it("getRecord deve reverter para token inexistente", async function () {
            const { nft } = await loadFixture(deployEducacaoFixture);
            await expect(nft.getRecord(999n)).to.be.reverted;
        });
    });
});
