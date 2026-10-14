package de.cardyssey.api

import com.zaxxer.hikari.HikariDataSource
import kotlinx.serialization.Serializable

@Serializable
data class PriceReviewCase(
 val languageCode:String,val cardId:String,val variantId:String,
 val searchStatus:String,val searchQuery:String?,val searchSteps:String,
 val candidates:String,val failureReason:String?,val checkedAt:String,
 val referencePriceEur:Double?,val referenceSource:String?,val referenceStatus:String?,
 val referenceVerification:String?
)

class AdminPriceReviewRepository(private val dataSource:HikariDataSource) {
 fun list(language:String?):List<PriceReviewCase> = dataSource.connection.use { connection ->
  val sql = """SELECT p.language_code,p.card_id,p.variant_id,p.search_status,p.search_query,
      p.search_steps::text,p.candidates::text,p.failure_reason,p.checked_at::text,
      r.price_eur,r.provider,r.verification_status,r.evidence->'verification'->'reasons' AS reference_verification
      FROM price_review_cases p
      LEFT JOIN price_reference_candidates r ON r.language_code=p.language_code AND r.card_id=p.card_id AND r.variant_id=p.variant_id AND r.provider='POKEMONTCGAPI_REFERENCE'
      LEFT JOIN tcg_price_cache c ON c.language_code=p.language_code
        AND c.card_id=p.card_id AND c.variant_id=p.variant_id
      WHERE (c.resolution_status IS NULL OR c.resolution_status <> 'PRICE_FOUND')
        AND (? IS NULL OR p.language_code=?)
      ORDER BY p.checked_at DESC,p.language_code,p.card_id LIMIT 2000"""
  connection.prepareStatement(sql).use { statement ->
   statement.setString(1,language)
   statement.setString(2,language)
   statement.executeQuery().use { rs ->
    buildList {
     while(rs.next()) add(PriceReviewCase(
      rs.getString(1),rs.getString(2),rs.getString(3),rs.getString(4),rs.getString(5),
      rs.getString(6),rs.getString(7),rs.getString(8),rs.getString(9),
      rs.getBigDecimal(10)?.toDouble(),rs.getString(11),rs.getString(12),rs.getString(13)))
    }
   }
  }
 }
}
