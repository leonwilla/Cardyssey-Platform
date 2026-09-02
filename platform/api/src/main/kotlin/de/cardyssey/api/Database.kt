package de.cardyssey.api

import com.zaxxer.hikari.HikariConfig
import com.zaxxer.hikari.HikariDataSource

fun createDataSource(): HikariDataSource {
    val config = HikariConfig().apply {
        jdbcUrl = requireEnv("DB_URL")
        username = requireEnv("DB_USER")
        password = requireEnv("DB_PASSWORD")

        maximumPoolSize = 10
        minimumIdle = 2

        connectionTimeout = 10_000
        idleTimeout = 600_000
        maxLifetime = 1_800_000

        poolName = "CardysseyPool"
    }

    return HikariDataSource(config)
}

fun requireEnv(name: String): String =
    System.getenv(name)
        ?.takeIf { it.isNotBlank() }
        ?: error("Missing environment variable: $name")
