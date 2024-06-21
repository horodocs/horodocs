async function main() {
    const Horodatage = await ethers.getContractFactory("Horodatage");
    const horo = await Horodatage.deploy("Horodatage");
    console.log("Contract Deployed to Address:", horo.address);
}
main()
    .then(() => process.exit(0))
    .catch(error => {
        console.error(error);
        process.exit(1);
    });