plugins {
    id("org.jetbrains.kotlin.jvm")
}

kotlin {
    jvmToolchain(17)
}

dependencies {
    testImplementation(kotlin("test"))
    testImplementation("org.json:json:20240303")
}

tasks.test {
    useJUnitPlatform()
    // vetores compartilhados com o app Windows e o firmware
    systemProperty("m88.vectors", rootProject.file("../protocol/vectors.json").absolutePath)
}
