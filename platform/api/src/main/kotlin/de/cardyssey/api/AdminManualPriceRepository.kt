package de.cardyssey.api

import com.zaxxer.hikari.HikariDataSource
import kotlinx.serialization.Serializable
import java.math.BigDecimal
import java.math.RoundingMode
import java.net.URI
import java.util.UUID

@Serializable
data class AdminManualPriceInput(
    val languageCode:String,
    val cardId:String,
    val variantId:String,
    val priceEur:Double,
    val condition:String,
    val sourceUrl:String,
    val note:String?=null,
    val exactPrintConfirmed:Boolean=false
)
@Serializable data class AdminManualPriceResult(val status:String,val baseEur:Double)

class AdminManualPriceRepository(private val ds:HikariDataSource) {
    fun apply(operator:UUID, input:AdminManualPriceInput):AdminManualPriceResult? {
        if (!input.exactPrintConfirmed ||
            input.languageCode !in setOf("de","en","ja","ko","zh-tw","zh-cn") ||
            input.cardId.isBlank() || input.cardId.length>100 ||
            input.variantId.isBlank() || input.variantId.length>140 ||
            !input.priceEur.isFinite() || input.priceEur<=0 || input.priceEur>1_000_000 ||
            input.sourceUrl.length>2000 ||
            input.note.orEmpty().length>500) return null
        val uri=runCatching { URI(input.sourceUrl.trim()) }.getOrNull() ?: return null
        if (uri.scheme!="https" || uri.host.isNullOrBlank() || uri.userInfo!=null) return null
        val condition=PricingCondition.parse(input.condition)
            ?.takeIf { it.name==input.condition.trim().uppercase() } ?: return null
        val base=BigDecimal.valueOf(input.priceEur)
            .divide(BigDecimal.valueOf(condition.factor),4,RoundingMode.HALF_UP)
        if (base<=BigDecimal.ZERO || base>BigDecimal("10000000")) return null
        return ds.connection.use { db ->
            db.autoCommit=false
            try {
                // Only exact physical variants that are currently held by someone
                // may be priced manually. No other users' identities are returned.
                val ownerCount=db.prepareStatement("""
                  SELECT COUNT(*) FROM collection_items
                  WHERE card_id=? AND language_code=? AND variant_id=?
                    AND deleted_at IS NULL
                """.trimIndent()).use { q ->
                    q.setString(1,input.cardId);q.setString(2,input.languageCode);q.setString(3,input.variantId)
                    q.executeQuery().use { r -> r.next();r.getLong(1) }
                }
                if(ownerCount==0L) { db.rollback();return null }
                val previous=db.prepareStatement("""
                    SELECT base_eur,resolution_status,source FROM tcg_price_cache
                    WHERE card_id=? AND language_code=? AND variant_id=? FOR UPDATE
                """.trimIndent()).use { q ->
                    q.setString(1,input.cardId);q.setString(2,input.languageCode);q.setString(3,input.variantId)
                    q.executeQuery().use { r ->
                        if(!r.next()) null else Triple(r.getBigDecimal(1),r.getString(2),r.getString(3))
                    }
                }
                if(previous==null || previous.second=="PRICE_FOUND") {db.rollback();return null}
                val changed=db.prepareStatement("""
                    UPDATE tcg_price_cache SET base_eur=?,source='ADMIN_MANUAL_VERIFIED',
                    updated_at=NOW(),resolution_status='PRICE_FOUND',
                    failure_detail=?,next_attempt_at=NOW()+INTERVAL '7 days'
                    WHERE card_id=? AND language_code=? AND variant_id=?
                      AND resolution_status IN ('NO_PRICE','NO_PUBLIC_PRICE','PROVIDER_ERROR')
                """.trimIndent()).use { q ->
                    q.setBigDecimal(1,base)
                    q.setString(2,"Admin exact-print review ${input.condition}; provenance recorded in price_manual_review_audit")
                    q.setString(3,input.cardId);q.setString(4,input.languageCode);q.setString(5,input.variantId)
                    q.executeUpdate()
                }
                if(changed!=1) {db.rollback();return null}
                db.prepareStatement("""
                    INSERT INTO tcg_price_history(card_id,language_code,variant_id,source,base_eur,captured_at)
                    VALUES(?,?,?,'ADMIN_MANUAL_VERIFIED',?,NOW())
                """.trimIndent()).use { q ->
                    q.setString(1,input.cardId);q.setString(2,input.languageCode);q.setString(3,input.variantId)
                    q.setBigDecimal(4,base);q.executeUpdate()
                }
                db.prepareStatement("""
                    INSERT INTO price_manual_review_audit(operator_id,language_code,card_id,variant_id,
                    source_url,entered_price_eur,entered_condition,stored_base_eur,
                    previous_base_eur,previous_status,previous_source,note)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                """.trimIndent()).use { q ->
                    q.setObject(1,operator);q.setString(2,input.languageCode)
                    q.setString(3,input.cardId);q.setString(4,input.variantId)
                    q.setString(5,input.sourceUrl.trim());q.setBigDecimal(6,BigDecimal.valueOf(input.priceEur))
                    q.setString(7,condition.name);q.setBigDecimal(8,base)
                    q.setBigDecimal(9,previous.first);q.setString(10,previous.second)
                    q.setString(11,previous.third);q.setString(12,input.note?.trim());q.executeUpdate()
                }
                db.commit()
                AdminManualPriceResult("saved",base.toDouble())
            } catch(e:Exception) {
                db.rollback()
                throw e
            } finally { db.autoCommit=true }
        }
    }
}
