export type AstrologyHighlight = {
  id: string;
  title: string;
  label: string;
  value: string;
  note?: string;
};

export type AmavasyaEvent = {
  name: string;
  displayDate: string;
  startIst: string;
  endIst: string;
  tithi: string;
  nakshatra: string;
  image: string;
  imageAlt: string;
  summary: string;
};

export const upcomingAmavasya: AmavasyaEvent = {
  name: "Bhadrapada Amavasya",
  displayDate: "11 September 2026",
  startIst: "10 September 2026 • 10:33 AM IST",
  endIst: "11 September 2026 • 08:56 AM IST",
  tithi: "Krishna Amavasya",
  nakshatra: "Purva Phalguni",
  image: "/images/astrology/amavasya-hero.webp",
  imageAlt: "Dark new moon sky illustration for Amavasya",
  summary:
    "Upcoming Amavasya with its Tithi and Nakshatra for the VenusRealm astrology page.",
};

export const astrologyHighlights: AstrologyHighlight[] = [
  {
    id: "amavasya-date",
    title: "Upcoming Amavasya",
    label: "Observed on",
    value: upcomingAmavasya.displayDate,
    note: upcomingAmavasya.name,
  },
  {
    id: "tithi",
    title: "Tithi",
    label: "Current lunar phase",
    value: upcomingAmavasya.tithi,
    note: `Begins ${upcomingAmavasya.startIst} • Ends ${upcomingAmavasya.endIst}`,
  },
  {
    id: "nakshatra",
    title: "Nakshatra",
    label: "Lunar mansion",
    value: upcomingAmavasya.nakshatra,
    note: "Reference display in IST; local timing can vary by city.",
  },
];
