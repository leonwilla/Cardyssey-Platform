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
    "Leon Willamowski";

  const street =
    process.env.LEGAL_OPERATOR_STREET?.trim() ||
    "Feldstiege 4a";

  const postalCity =
    process.env.LEGAL_OPERATOR_POSTAL_CITY?.trim() ||
    "48161 Münster";

  const country =
    process.env.LEGAL_OPERATOR_COUNTRY?.trim() ||
    "Deutschland";

  const email =
    process.env.LEGAL_CONTACT_EMAIL?.trim() ||
    "kontakt@cardyssey.de";

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
