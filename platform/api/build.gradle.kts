plugins {
    kotlin("jvm") version "2.1.20"
    kotlin("plugin.serialization") version "2.1.20"
    application
}

group = "de.cardyssey"
version = "0.2.0"

repositories {
    mavenCentral()
}

dependencies {
    implementation("io.ktor:ktor-server-core-jvm:3.1.3")
    implementation("io.ktor:ktor-server-netty-jvm:3.1.3")
    implementation("io.ktor:ktor-server-content-negotiation-jvm:3.1.3")
    implementation("io.ktor:ktor-serialization-kotlinx-json-jvm:3.1.3")
    implementation("io.ktor:ktor-server-call-logging-jvm:3.1.3")
    implementation("io.ktor:ktor-server-status-pages-jvm:3.1.3")
    implementation("io.ktor:ktor-server-cors-jvm:3.1.3")

    implementation("io.ktor:ktor-server-auth-jvm:3.1.3")
    implementation("io.ktor:ktor-server-auth-jwt-jvm:3.1.3")

    implementation("com.zaxxer:HikariCP:6.2.1")
    implementation("org.postgresql:postgresql:42.7.5")

    implementation("org.flywaydb:flyway-core:13.8.1")
    implementation("org.flywaydb:flyway-database-postgresql:13.8.1")

    implementation("de.mkammerer:argon2-jvm:2.11")
    implementation("org.jsoup:jsoup:1.18.3")
    implementation("org.seleniumhq.selenium:selenium-java:4.35.0")

    implementation("ch.qos.logback:logback-classic:1.5.18")
    implementation("com.google.firebase:firebase-admin:9.6.0")

    testImplementation(kotlin("test-junit5"))
}

application {
    mainClass.set("de.cardyssey.api.ApplicationKt")
}

tasks.test {
    useJUnitPlatform()
}

kotlin {
    jvmToolchain(21)
}
