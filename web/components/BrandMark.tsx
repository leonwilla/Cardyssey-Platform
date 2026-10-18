import Image from "next/image";
export function BrandMark() {
  return (
    <span
      className="brandMark"
      aria-hidden="true"
    >
      <Image width={64} height={64}
        src="/cardyssey-emblem-gold.png"
        alt=""
      />
    </span>
  );
}
