import { clsx } from "clsx";
import { twMerge } from "tailwind-merge"

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export const NO_IMAGE_PLACEHOLDER = `data:image/svg+xml;utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 200' width='100%25' height='100%25'%3E%3Crect width='100%25' height='100%25' fill='%23f8fafc'/%3E%3Cg transform='translate(0, 10)'%3E%3Crect x='80' y='60' width='40' height='40' rx='8' fill='none' stroke='%23cbd5e1' stroke-width='2'/%3E%3Ccircle cx='92' cy='72' r='3' fill='%23cbd5e1'/%3E%3Cpath d='M82 98l10-10 12 12' stroke='%23cbd5e1' stroke-width='2' fill='none' stroke-linejoin='round'/%3E%3Cpath d='M96 92l6-6 16 16' stroke='%23cbd5e1' stroke-width='2' fill='none' stroke-linejoin='round'/%3E%3Ctext x='50%25' y='130' dominant-baseline='middle' text-anchor='middle' font-family='sans-serif' font-size='14' font-weight='500' fill='%2394a3b8'%3ENo Image%3C/text%3E%3C/g%3E%3C/svg%3E`;
