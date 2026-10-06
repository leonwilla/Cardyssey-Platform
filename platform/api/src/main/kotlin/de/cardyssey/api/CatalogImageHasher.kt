package de.cardyssey.api

import java.awt.Graphics2D
import java.awt.RenderingHints
import java.awt.image.BufferedImage
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.net.URI
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse
import java.nio.file.Files
import java.nio.file.Path
import java.nio.file.StandardCopyOption
import java.time.Duration
import javax.imageio.ImageIO

class CatalogImageHasher {
    private val http =
        HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(15))
            .followRedirects(HttpClient.Redirect.NORMAL)
            .build()

    fun downloadAndHash(
        imageBase: String,
        destination: Path
    ): Pair<Long, Long> {
        val path =
            imageBase.substringBefore("?").lowercase()

        val url =
            when {
                listOf(".jpg", ".jpeg", ".png", ".webp")
                    .any(path::endsWith) -> imageBase
                path.startsWith("https://img.ricardostatic.ch/") ||
                    path.startsWith("https://img.kleinanzeigen.de/") -> imageBase
                path.startsWith("https://assets.tcgdex.net/") ->
                    imageBase.removeSuffix("/") + "/high.webp"
                else ->
                    imageBase.removeSuffix("/") + "/low.jpg"
            }

        val request =
            HttpRequest.newBuilder()
                .uri(URI.create(url))
                .timeout(Duration.ofSeconds(30))
                .header("Accept", "image/jpeg,image/webp,image/*")
                .header("User-Agent", "Cardyssey-CatalogMirror/1.0")
                .GET()
                .build()

        val response =
            http.send(
                request,
                HttpResponse.BodyHandlers.ofByteArray()
            )

        check(response.statusCode() in 200..299) {
            "Image returned HTTP ${response.statusCode()}: $url"
        }

        val bytes = response.body()
        check(bytes.isNotEmpty()) {
            "Image was empty: $url"
        }

        val decoded =
            ImageIO.read(ByteArrayInputStream(bytes))
                ?: error("Unsupported catalog image: $url")

        val rgb =
            BufferedImage(
                decoded.width,
                decoded.height,
                BufferedImage.TYPE_INT_RGB
            )

        val graphics =
            rgb.createGraphics()

        try {
            graphics.drawImage(decoded, 0, 0, null)
        } finally {
            graphics.dispose()
        }

        val encoded =
            ByteArrayOutputStream().use { output ->
                check(ImageIO.write(rgb, "jpg", output)) {
                    "JPEG encoder unavailable"
                }
                output.toByteArray()
            }

        val hash =
            differenceHash(
                normalizeCard(rgb)
            )

        Files.createDirectories(destination.parent)

        val temporary =
            Files.createTempFile(
                destination.parent,
                destination.fileName.toString(),
                ".part"
            )

        try {
            Files.write(temporary, encoded)
            Files.move(
                temporary,
                destination,
                StandardCopyOption.REPLACE_EXISTING,
                StandardCopyOption.ATOMIC_MOVE
            )
        } finally {
            Files.deleteIfExists(temporary)
        }

        return hash to encoded.size.toLong()
    }

    fun hash(bytes: ByteArray): Long {
        val decoded =
            ImageIO.read(ByteArrayInputStream(bytes))
                ?: error("Unsupported recognition image")

        return differenceHash(normalizeCard(decoded))
    }

    private fun normalizeCard(source: BufferedImage): BufferedImage {
        require(source.width > 0 && source.height > 0) {
            "Catalog image has invalid dimensions: " + source.width + "x" + source.height
        }

        val targetRatio = 63.0 / 88.0
        val sourceRatio = source.width.toDouble() / source.height.toDouble()

        val cropWidth: Int
        val cropHeight: Int

        if (sourceRatio > targetRatio) {
            cropHeight = source.height
            cropWidth = (cropHeight * targetRatio).toInt().coerceIn(1, source.width)
        } else {
            cropWidth = source.width
            cropHeight = (cropWidth / targetRatio).toInt().coerceIn(1, source.height)
        }

        val left = ((source.width - cropWidth) / 2).coerceAtLeast(0)
        val top = ((source.height - cropHeight) / 2).coerceAtLeast(0)

        // Render the crop into a fresh raster instead of returning getSubimage().
        // Some ImageIO/WebP decoders expose rasters with offsets/strides that can
        // later throw "Coordinate out of bounds" during perceptual hashing.
        val normalized =
            BufferedImage(
                cropWidth,
                cropHeight,
                BufferedImage.TYPE_INT_RGB
            )
        val graphics = normalized.createGraphics()
        try {
            graphics.drawImage(
                source,
                0,
                0,
                cropWidth,
                cropHeight,
                left,
                top,
                left + cropWidth,
                top + cropHeight,
                null
            )
        } finally {
            graphics.dispose()
        }
        return normalized
    }

    private fun differenceHash(source: BufferedImage): Long {
        val resized =
            BufferedImage(
                9,
                8,
                BufferedImage.TYPE_BYTE_GRAY
            )

        val graphics: Graphics2D = resized.createGraphics()

        try {
            graphics.setRenderingHint(
                RenderingHints.KEY_INTERPOLATION,
                RenderingHints.VALUE_INTERPOLATION_BILINEAR
            )
            graphics.drawImage(source, 0, 0, 9, 8, null)
        } finally {
            graphics.dispose()
        }

        var value = 0L
        var bit = 0

        for (y in 0 until 8) {
            for (x in 0 until 8) {
                val left = resized.raster.getSample(x, y, 0)
                val right = resized.raster.getSample(x + 1, y, 0)

                if (left > right) {
                    value = value or (1L shl bit)
                }

                bit += 1
            }
        }

        return value
    }
}
