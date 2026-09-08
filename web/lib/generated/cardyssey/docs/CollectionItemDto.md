
# CollectionItemDto


## Properties

Name | Type
------------ | -------------
`id` | string
`key` | string
`cardId` | string
`languageCode` | string
`name` | string
`setId` | string
`setName` | string
`localId` | string
`imageBase` | string
`imageLanguage` | string
`variant` | string
`variantSpec` | [VariantSpecDto](VariantSpecDto.md)
`condition` | string
`quantity` | number
`unitEur` | number
`unitUsd` | number
`marketUnitEur` | { [key: string]: number; }
`marketUpdatedAtMs` | { [key: string]: number; }
`marketSampleCount` | { [key: string]: number; }

## Example

```typescript
import type { CollectionItemDto } from 'cardyssey-contract'

// TODO: Update the object below with actual values
const example = {
  "id": null,
  "key": null,
  "cardId": null,
  "languageCode": null,
  "name": null,
  "setId": null,
  "setName": null,
  "localId": null,
  "imageBase": null,
  "imageLanguage": null,
  "variant": null,
  "variantSpec": null,
  "condition": null,
  "quantity": null,
  "unitEur": null,
  "unitUsd": null,
  "marketUnitEur": null,
  "marketUpdatedAtMs": null,
  "marketSampleCount": null,
} satisfies CollectionItemDto

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as CollectionItemDto
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


