
# EbayRecentSaleResponse


## Properties

Name | Type
------------ | -------------
`itemId` | string
`title` | string
`soldPriceEur` | number
`rawCondition` | string
`endedAt` | string
`url` | string

## Example

```typescript
import type { EbayRecentSaleResponse } from 'cardyssey-contract'

// TODO: Update the object below with actual values
const example = {
  "itemId": null,
  "title": null,
  "soldPriceEur": null,
  "rawCondition": null,
  "endedAt": null,
  "url": null,
} satisfies EbayRecentSaleResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as EbayRecentSaleResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


