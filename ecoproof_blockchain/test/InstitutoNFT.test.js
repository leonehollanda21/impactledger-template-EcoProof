const { expect } = require("chai");
const { ethers, upgrades } = require("hardhat");
const { loadFixture } = require("@nomicfoundation/hardhat-network-helpers");
const { MerkleTree } = require("merkletreejs");

function toBytes32(str) {
    return ethers.keccak256(ethers.toUtf8Bytes(str));
}

describe("InstitutoNFT (Soulbound ECOE + Merkle Tree)", function () {
    const METADATA_URI = "ipfs://QmTest123/metadata.json";
    const ActionType = { LIXO_RUA: 0, PRAIA: 1, CORREGO: 2, QUEIMADA: 3, OUTRO: 4 };
    const EIP5192_INTERFACE_ID = "0xb45a3c0e";

    async function deployInstitutoFixture() {
        const [admin, minter, institute, citizen1, citizen2, citizen3, stranger] = await ethers.getSigners();

        const InstitutoNFT = await ethers.getContractFactory("InstitutoNFT");
        const nft = await upgrades.deployProxy(
            InstitutoNFT,
            [admin.address, minter.address],
            { initializer: "initialize", kind: "uups" }
        );
        await nft.waitForDeployment();

        // Grant INSTITUTE_ROLE to the institute signer
        const INSTITUTE_ROLE = await nft.INSTITUTE_ROLE();
        await nft.connect(admin).grantRole(INSTITUTE_ROLE, institute.address);

        return { nft, admin, minter, institute, citizen1, citizen2, citizen3, stranger };
    }

    function buildMerkleTree(addresses) {
        const leaves = addresses.map(addr => 
            ethers.keccak256(ethers.solidityPacked(["address"], [addr]))
        );
        const tree = new MerkleTree(leaves, ethers.keccak256, { sortPairs: true });
        return tree;
    }

    describe("Deploy e Inicializacao", function () {
        it("deve configurar nome e simbolo como EcoProof Evento (ECOE)", async function () {
            const { nft } = await loadFixture(deployInstitutoFixture);
            expect(await nft.name()).to.equal("EcoProof Evento");
            expect(await nft.symbol()).to.equal("ECOE");
        });

        it("deve suportar EIP-5192 (Soulbound)", async function () {
            const { nft } = await loadFixture(deployInstitutoFixture);
            expect(await nft.supportsInterface(EIP5192_INTERFACE_ID)).to.be.true;
        });

        it("deve atribuir roles iniciais corretamente", async function () {
            const { nft, admin, minter, institute } = await loadFixture(deployInstitutoFixture);
            
            expect(await nft.hasRole(await nft.MINTER_ROLE(), minter.address)).to.be.true;
            expect(await nft.hasRole(await nft.UPGRADER_ROLE(), admin.address)).to.be.true;
            expect(await nft.hasRole(await nft.INSTITUTE_ROLE(), institute.address)).to.be.true;
        });
    });

    describe("Soulbound (EIP-5192)", function () {
        it("deve bloquear transferencias apos mint direto", async function () {
            const { nft, minter, citizen1, citizen2 } = await loadFixture(deployInstitutoFixture);
            
            await nft.connect(minter).mintEvento(
                citizen1.address, METADATA_URI, toBytes32("evt-1"),
                ActionType.PRAIA, minter.address, 1
            );

            await expect(
                nft.connect(citizen1).transferFrom(citizen1.address, citizen2.address, 1n)
            ).to.be.revertedWithCustomError(nft, "SoulboundNaoTransferivel");
        });

        it("locked() deve retornar true para tokens mintados", async function () {
            const { nft, minter, citizen1 } = await loadFixture(deployInstitutoFixture);
            
            await nft.connect(minter).mintEvento(
                citizen1.address, METADATA_URI, toBytes32("evt-1"),
                ActionType.PRAIA, minter.address, 1
            );

            expect(await nft.locked(1n)).to.be.true;
        });
    });

    describe("mintEvento (direto pelo backend)", function () {
        it("deve mintar e emitir NFTEventoMintado + Locked", async function () {
            const { nft, minter, citizen1, institute } = await loadFixture(deployInstitutoFixture);
            const offchainId = toBytes32("part-001");

            const tx = await nft.connect(minter).mintEvento(
                citizen1.address, METADATA_URI, offchainId,
                ActionType.PRAIA, institute.address, 42
            );

            await expect(tx)
                .to.emit(nft, "NFTEventoMintado")
                .withArgs(1n, citizen1.address, institute.address, ActionType.PRAIA, offchainId, 42);

            await expect(tx).to.emit(nft, "Locked").withArgs(1n);

            expect(await nft.ownerOf(1n)).to.equal(citizen1.address);
        });

        it("deve rejeitar re-mint do mesmo offchainId", async function () {
            const { nft, minter, citizen1, institute } = await loadFixture(deployInstitutoFixture);
            const offchainId = toBytes32("part-001");

            await nft.connect(minter).mintEvento(
                citizen1.address, METADATA_URI, offchainId,
                ActionType.PRAIA, institute.address, 1
            );

            await expect(
                nft.connect(minter).mintEvento(
                    citizen1.address, METADATA_URI, offchainId,
                    ActionType.PRAIA, institute.address, 1
                )
            ).to.be.revertedWithCustomError(nft, "AlreadyMinted");
        });

        it("deve rejeitar mint sem MINTER_ROLE", async function () {
            const { nft, stranger, citizen1 } = await loadFixture(deployInstitutoFixture);
            
            await expect(
                nft.connect(stranger).mintEvento(
                    citizen1.address, METADATA_URI, toBytes32("x"),
                    ActionType.PRAIA, stranger.address, 1
                )
            ).to.be.revertedWithCustomError(nft, "AccessControlUnauthorizedAccount");
        });
    });

    describe("mintBatch", function () {
        it("deve mintar em lote e emitir BatchMinted", async function () {
            const { nft, minter, citizen1, citizen2, institute } = await loadFixture(deployInstitutoFixture);
            const eventHash = toBytes32("event-hash-1");

            const params = [
                { to: citizen1.address, uri: METADATA_URI, offchainId: toBytes32("bp-1"), actionType: ActionType.PRAIA, institutionWallet: institute.address },
                { to: citizen2.address, uri: METADATA_URI, offchainId: toBytes32("bp-2"), actionType: ActionType.PRAIA, institutionWallet: institute.address },
            ];

            await expect(nft.connect(minter).mintBatch(params, eventHash, 1))
                .to.emit(nft, "BatchMinted")
                .withArgs(eventHash, institute.address, 2n);

            expect(await nft.totalSupply()).to.equal(2n);
        });
    });

    describe("Merkle Tree Claim", function () {
        it("setMerkleRoot deve funcionar com INSTITUTE_ROLE", async function () {
            const { nft, institute, citizen1, citizen2 } = await loadFixture(deployInstitutoFixture);

            const tree = buildMerkleTree([citizen1.address, citizen2.address]);
            const root = tree.getHexRoot();

            await expect(nft.connect(institute).setMerkleRoot(1, root))
                .to.emit(nft, "MerkleRootSet")
                .withArgs(1, root, institute.address);

            expect(await nft.eventoMerkleRoot(1)).to.equal(root);
        });

        it("setMerkleRoot deve rejeitar sem INSTITUTE_ROLE", async function () {
            const { nft, stranger } = await loadFixture(deployInstitutoFixture);

            await expect(
                nft.connect(stranger).setMerkleRoot(1, toBytes32("root"))
            ).to.be.revertedWithCustomError(nft, "AccessControlUnauthorizedAccount");
        });

        it("claimNFT deve funcionar com proof valido", async function () {
            const { nft, institute, citizen1, citizen2 } = await loadFixture(deployInstitutoFixture);

            const tree = buildMerkleTree([citizen1.address, citizen2.address]);
            const root = tree.getHexRoot();

            await nft.connect(institute).setMerkleRoot(1, root);

            // Get proof for citizen1
            const leaf = ethers.keccak256(ethers.solidityPacked(["address"], [citizen1.address]));
            const proof = tree.getHexProof(leaf);

            const tx = await nft.connect(citizen1).claimNFT(1, proof, METADATA_URI);

            await expect(tx).to.emit(nft, "NFTClaimed");
            await expect(tx).to.emit(nft, "Locked");

            expect(await nft.ownerOf(1n)).to.equal(citizen1.address);
            expect(await nft.claimed(1, citizen1.address)).to.be.true;
        });

        it("deve rejeitar claim duplicado", async function () {
            const { nft, institute, citizen1 } = await loadFixture(deployInstitutoFixture);

            const tree = buildMerkleTree([citizen1.address]);
            const root = tree.getHexRoot();
            await nft.connect(institute).setMerkleRoot(1, root);

            const leaf = ethers.keccak256(ethers.solidityPacked(["address"], [citizen1.address]));
            const proof = tree.getHexProof(leaf);

            await nft.connect(citizen1).claimNFT(1, proof, METADATA_URI);

            await expect(
                nft.connect(citizen1).claimNFT(1, proof, METADATA_URI)
            ).to.be.revertedWithCustomError(nft, "AlreadyClaimed");
        });

        it("deve rejeitar proof invalido", async function () {
            const { nft, institute, citizen1, stranger } = await loadFixture(deployInstitutoFixture);

            const tree = buildMerkleTree([citizen1.address]);
            const root = tree.getHexRoot();
            await nft.connect(institute).setMerkleRoot(1, root);

            // stranger's proof is invalid
            const leaf = ethers.keccak256(ethers.solidityPacked(["address"], [citizen1.address]));
            const proof = tree.getHexProof(leaf);

            await expect(
                nft.connect(stranger).claimNFT(1, proof, METADATA_URI)
            ).to.be.revertedWithCustomError(nft, "InvalidMerkleProof");
        });

        it("deve rejeitar claim sem Merkle Root definido", async function () {
            const { nft, citizen1 } = await loadFixture(deployInstitutoFixture);

            await expect(
                nft.connect(citizen1).claimNFT(999, [], METADATA_URI)
            ).to.be.revertedWithCustomError(nft, "MerkleRootNotSet");
        });
    });
});
