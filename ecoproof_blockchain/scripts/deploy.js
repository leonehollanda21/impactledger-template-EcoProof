const { ethers, upgrades } = require("hardhat");
const fs = require("fs/promises");
const path = require("path");

async function main() {
    console.log("╔══════════════════════════════════════════════════════════╗");
    console.log("║   EcoProof Blockchain — Deploy Completo                  ║");
    console.log("║   5 contratos: NFT + InstitutoNFT + EducacaoNFT + Registry ║");
    console.log("║   + DenunciaNFT                                          ║");
    console.log("╚══════════════════════════════════════════════════════════╝\n");

    const [deployer] = await ethers.getSigners();
    const network = await ethers.provider.getNetwork();

    console.log(`Network: ${network.name} (chainId: ${network.chainId})`);
    console.log(`Deployer: ${deployer.address}`);

    const balance = await ethers.provider.getBalance(deployer.address);
    console.log(`Balance: ${ethers.formatEther(balance)} ETH/MATIC\n`);

    const adminWallet = process.env.ADMIN_WALLET || deployer.address;
    const minterWallet = deployer.address;

    // ══════════════════════════════════════════════════════════════════════════
    //  1. EcoProofRegistry (não-upgradeable — imutável por design)
    // ══════════════════════════════════════════════════════════════════════════
    console.log("━━━ 1/4 ━━━ Deploying EcoProofRegistry (Proof of Existence)...");
    const Registry = await ethers.getContractFactory("EcoProofRegistry");
    const registry = await Registry.deploy(adminWallet, minterWallet);
    await registry.waitForDeployment();

    const registryAddress = await registry.getAddress();
    console.log(`✅ EcoProofRegistry deployed at: ${registryAddress}\n`);

    // ══════════════════════════════════════════════════════════════════════════
    //  2. EcoProofNFT — ECOI (UUPS Proxy, Soulbound EIP-5192)
    // ══════════════════════════════════════════════════════════════════════════
    console.log("━━━ 2/4 ━━━ Deploying EcoProofNFT Proxy (Soulbound ECOI)...");
    const NFT = await ethers.getContractFactory("EcoProofNFT");
    const nft = await upgrades.deployProxy(NFT, [adminWallet, minterWallet], {
        initializer: "initialize",
        kind: "uups",
    });
    await nft.waitForDeployment();

    const nftAddress = await nft.getAddress();
    const nftImplAddr = await upgrades.erc1967.getImplementationAddress(nftAddress);

    console.log(`✅ EcoProofNFT Proxy:          ${nftAddress}`);
    console.log(`   Implementation:             ${nftImplAddr}\n`);

    // ══════════════════════════════════════════════════════════════════════════
    //  3. InstitutoNFT — ECOE (UUPS Proxy, Soulbound EIP-5192 + Merkle)
    // ══════════════════════════════════════════════════════════════════════════
    console.log("━━━ 3/4 ━━━ Deploying InstitutoNFT Proxy (Soulbound ECOE + Merkle)...");
    const InstitutoNFT = await ethers.getContractFactory("InstitutoNFT");
    const institutoNft = await upgrades.deployProxy(InstitutoNFT, [adminWallet, minterWallet], {
        initializer: "initialize",
        kind: "uups",
    });
    await institutoNft.waitForDeployment();

    const institutoNftAddress = await institutoNft.getAddress();
    const institutoImplAddr = await upgrades.erc1967.getImplementationAddress(institutoNftAddress);

    console.log(`✅ InstitutoNFT Proxy:          ${institutoNftAddress}`);
    console.log(`   Implementation:              ${institutoImplAddr}\n`);

    // ══════════════════════════════════════════════════════════════════════════
    //  4. EducacaoNFT — ECED (UUPS Proxy, Soulbound EIP-5192)
    // ══════════════════════════════════════════════════════════════════════════
    console.log("━━━ 4/4 ━━━ Deploying EducacaoNFT Proxy (Soulbound ECED — Educação Ambiental)...");
    const EducacaoNFT = await ethers.getContractFactory("EducacaoNFT");
    const educacaoNft = await upgrades.deployProxy(EducacaoNFT, [adminWallet, minterWallet], {
        initializer: "initialize",
        kind: "uups",
    });
    await educacaoNft.waitForDeployment();

    const educacaoNftAddress = await educacaoNft.getAddress();
    const educacaoImplAddr = await upgrades.erc1967.getImplementationAddress(educacaoNftAddress);

    console.log(`✅ EducacaoNFT Proxy:           ${educacaoNftAddress}`);
    console.log(`   Implementation:              ${educacaoImplAddr}\n`);

    // ══════════════════════════════════════════════════════════════════════════
    //  5. DenunciaNFT — ECFD (UUPS Proxy, Soulbound EIP-5192)
    // ══════════════════════════════════════════════════════════════════════════
    console.log("━━━ 5/5 ━━━ Deploying DenunciaNFT Proxy (Soulbound ECFD — Denúncia Ambiental Verificada)...");
    const DenunciaNFT = await ethers.getContractFactory("DenunciaNFT");
    const denunciaNft = await upgrades.deployProxy(DenunciaNFT, [adminWallet, minterWallet], {
        initializer: "initialize",
        kind: "uups",
    });
    await denunciaNft.waitForDeployment();

    const denunciaNftAddress = await denunciaNft.getAddress();
    const denunciaImplAddr = await upgrades.erc1967.getImplementationAddress(denunciaNftAddress);

    console.log(`✅ DenunciaNFT Proxy:            ${denunciaNftAddress}`);
    console.log(`   Implementation:               ${denunciaImplAddr}\n`);

    // ══════════════════════════════════════════════════════════════════════════
    //  6. Post-Deployment Role Validation
    // ══════════════════════════════════════════════════════════════════════════
    console.log("━━━ Validating access controls ━━━");

    const checks = [
        { contract: "EcoProofNFT", fn: async () => await nft.hasRole(await nft.MINTER_ROLE(), minterWallet), label: "MINTER_ROLE" },
        { contract: "EcoProofNFT", fn: async () => await nft.hasRole(await nft.UPGRADER_ROLE(), adminWallet), label: "UPGRADER_ROLE" },
        { contract: "EcoProofNFT", fn: async () => await nft.hasRole(await nft.PAUSER_ROLE(), adminWallet), label: "PAUSER_ROLE" },
        
        { contract: "InstitutoNFT", fn: async () => await institutoNft.hasRole(await institutoNft.MINTER_ROLE(), minterWallet), label: "MINTER_ROLE" },
        { contract: "InstitutoNFT", fn: async () => await institutoNft.hasRole(await institutoNft.UPGRADER_ROLE(), adminWallet), label: "UPGRADER_ROLE" },
        
        { contract: "EducacaoNFT", fn: async () => await educacaoNft.hasRole(await educacaoNft.MINTER_ROLE(), minterWallet), label: "MINTER_ROLE" },
        { contract: "EducacaoNFT", fn: async () => await educacaoNft.hasRole(await educacaoNft.UPGRADER_ROLE(), adminWallet), label: "UPGRADER_ROLE" },
        { contract: "EducacaoNFT", fn: async () => await educacaoNft.hasRole(await educacaoNft.PAUSER_ROLE(), adminWallet), label: "PAUSER_ROLE" },
        { contract: "DenunciaNFT", fn: async () => await denunciaNft.hasRole(await denunciaNft.MINTER_ROLE(), minterWallet), label: "MINTER_ROLE" },
        { contract: "DenunciaNFT", fn: async () => await denunciaNft.hasRole(await denunciaNft.UPGRADER_ROLE(), adminWallet), label: "UPGRADER_ROLE" },
        { contract: "DenunciaNFT", fn: async () => await denunciaNft.hasRole(await denunciaNft.PAUSER_ROLE(), adminWallet), label: "PAUSER_ROLE" },
    ];

    let allPassed = true;
    for (const check of checks) {
        const ok = await check.fn();
        console.log(`  ${ok ? "✅" : "❌"} ${check.contract}.${check.label}: ${ok}`);
        if (!ok) allPassed = false;
    }

    if (!allPassed) {
        console.warn("\n⚠️  WARNING: Some role validations failed. Check contract initialization.");
    }

    // ══════════════════════════════════════════════════════════════════════════
    //  7. Verify EIP-5192 (Soulbound)
    // ══════════════════════════════════════════════════════════════════════════
    console.log("\n━━━ Verifying EIP-5192 support ━━━");
    const EIP5192_ID = "0xb45a3c0e";
    const nftSupports = await nft.supportsInterface(EIP5192_ID);
    const institutoSupports = await institutoNft.supportsInterface(EIP5192_ID);
    const educacaoSupports = await educacaoNft.supportsInterface(EIP5192_ID);
    const denunciaSupports = await denunciaNft.supportsInterface(EIP5192_ID);
    console.log(`  EcoProofNFT   supports EIP-5192: ${nftSupports ? "✅" : "❌"}`);
    console.log(`  InstitutoNFT  supports EIP-5192: ${institutoSupports ? "✅" : "❌"}`);
    console.log(`  EducacaoNFT   supports EIP-5192: ${educacaoSupports ? "✅" : "❌"}`);
    console.log(`  DenunciaNFT   supports EIP-5192: ${denunciaSupports ? "✅" : "❌"}`);

    // ══════════════════════════════════════════════════════════════════════════
    //  8. ABI Export
    // ══════════════════════════════════════════════════════════════════════════
    await exportAbis();

    // ══════════════════════════════════════════════════════════════════════════
    //  9. Output for Backend Integration
    // ══════════════════════════════════════════════════════════════════════════
    console.log("\n╔══════════════════════════════════════════════════╗");
    console.log("║   Deployment Complete — Backend .env values:     ║");
    console.log("╚══════════════════════════════════════════════════╝");
    console.log(`NFT_CONTRACT_ADDRESS=${nftAddress}`);
    console.log(`INSTITUTO_NFT_CONTRACT_ADDRESS=${institutoNftAddress}`);
    console.log(`EDUCACAO_NFT_CONTRACT_ADDRESS=${educacaoNftAddress}`);
    console.log(`DENUNCIA_NFT_CONTRACT_ADDRESS=${denunciaNftAddress}`);
    console.log(`REGISTRY_CONTRACT_ADDRESS=${registryAddress}`);
    console.log(`BLOCKCHAIN_ENABLED=true`);
    console.log("");
}

async function exportAbis() {
    console.log("\n━━━ Exporting ABIs for backend integration ━━━");

    const artifactsDir = path.join(__dirname, "..", "artifacts", "contracts");
    // Export to both backend app/abi and a local abi directory
    const destinations = [
        path.join(__dirname, "..", "..", "Backend_web3", "app", "abi"),
        path.join(__dirname, "..", "abi"),
    ];

    const contracts = ["EcoProofNFT", "InstitutoNFT", "EducacaoNFT", "EcoProofRegistry", "DenunciaNFT"];

    for (const destDir of destinations) {
        try {
            await fs.access(destDir);
        } catch {
            await fs.mkdir(destDir, { recursive: true });
        }

        for (const name of contracts) {
            const artifactPath = path.join(artifactsDir, `${name}.sol`, `${name}.json`);

            try {
                const artifactData = await fs.readFile(artifactPath, "utf8");
                const artifact = JSON.parse(artifactData);

                const abiOnly = { contractName: name, abi: artifact.abi };
                const destPath = path.join(destDir, `${name}.json`);

                await fs.writeFile(destPath, JSON.stringify(abiOnly, null, 2));
                console.log(`  ✅ ABI exported: ${path.relative(process.cwd(), destPath)}`);
            } catch (error) {
                console.error(`  ❌ Failed to export ABI for ${name}: ${error.message}`);
            }
        }
    }
}

main().catch((err) => {
    console.error("Fatal deployment error:", err);
    process.exitCode = 1;
});