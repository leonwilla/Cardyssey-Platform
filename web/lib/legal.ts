export type LegalOperator = {
  name: string;
  street: string;
  postalCity: string;
  country: string;
  email: string;
  complete: boolean;
};

export function legalOperator(): LegalOperator {
  const name =
    process.env.LEGAL_OPERATOR_NAME?.trim() ||
    "Cardyssey";

  const street =
    process.env.LEGAL_OPERATOR_STREET?.trim() ||
    "";

  const postalCity =
    process.env.LEGAL_OPERATOR_POSTAL_CITY?.trim() ||
    "";

  const country =
    process.env.LEGAL_OPERATOR_COUNTRY?.trim() ||
    "Deutschland";

  const email =
    process.env.LEGAL_CONTACT_EMAIL?.trim() ||
    "";

  return {
    name,
    street,
    postalCity,
    country,
    email,
    complete:
      Boolean(name) &&
      Boolean(street) &&
      Boolean(postalCity) &&
      Boolean(email),
  };
}
