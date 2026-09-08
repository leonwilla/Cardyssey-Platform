
# FriendSetProgressResponse


## Properties

Name | Type
------------ | -------------
`setId` | string
`setName` | string
`ownedCards` | number
`totalCards` | number

## Example

```typescript
import type { FriendSetProgressResponse } from 'cardyssey-contract'

// TODO: Update the object below with actual values
const example = {
  "setId": null,
  "setName": null,
  "ownedCards": null,
  "totalCards": null,
} satisfies FriendSetProgressResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as FriendSetProgressResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


