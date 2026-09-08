
# FriendProfileResponse


## Properties

Name | Type
------------ | -------------
`friendCode` | string
`displayName` | string
`avatarUrl` | string
`isFriend` | boolean
`canSeeShowcase` | boolean
`canSeeCollection` | boolean
`canSeeCollectionValue` | boolean
`canSeeQuantity` | boolean
`canSeeSets` | boolean
`canSeeWishlist` | boolean

## Example

```typescript
import type { FriendProfileResponse } from 'cardyssey-contract'

// TODO: Update the object below with actual values
const example = {
  "friendCode": null,
  "displayName": null,
  "avatarUrl": null,
  "isFriend": null,
  "canSeeShowcase": null,
  "canSeeCollection": null,
  "canSeeCollectionValue": null,
  "canSeeQuantity": null,
  "canSeeSets": null,
  "canSeeWishlist": null,
} satisfies FriendProfileResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as FriendProfileResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


