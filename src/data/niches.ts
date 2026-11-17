// Landing pages for the kinds of businesses we pitch most. One page each at
// /websites-for/<slug>. Copy stays short and factual: no invented stats or reviews.

export type Niche = {
  slug: string;
  plural: string;
  singular: string;
  title: [string, string];
  intro: string;
  includes: string[];
  packageId: string;
  // Only projects that genuinely relate. Otherwise recent work is shown instead.
  related: string[];
};

export const niches: Niche[] = [
  {
    slug: "clinics",
    plural: "Clinics",
    singular: "clinic",
    title: ["A clinic website", "patients trust."],
    intro:
      "Show your doctors, timings and services, and let patients call or message you in one tap. Built to load fast on phones and to show up when people search nearby.",
    includes: [
      "Doctor profiles and specialities",
      "Timings, address and Google Maps",
      "Appointment requests on WhatsApp or call",
      "A page for each service, written for Google",
      "Fast on every phone, even on slow data",
    ],
    packageId: "synex-starter-website",
    related: ["dialysisongo", "vitalwatch-365", "appy-saude"],
  },
  {
    slug: "dentists",
    plural: "Dentists",
    singular: "dental clinic",
    title: ["A dental website", "that fills your chair."],
    intro:
      "Explain your treatments in plain words, show your clinic and team, and make booking a check-up one tap away.",
    includes: [
      "Treatment pages for cleaning, braces, implants and more",
      "Clinic photos and your team",
      "Book a visit on WhatsApp or call",
      "Link to your Google rating and reviews",
      "Timings, address and directions",
    ],
    packageId: "synex-starter-website",
    related: ["dialysisongo", "vitalwatch-365"],
  },
  {
    slug: "salons",
    plural: "Salons",
    singular: "salon",
    title: ["A salon website", "that gets you booked."],
    intro:
      "Your services and prices in one clean place, your best work up front, and booking on WhatsApp so clients do not have to call.",
    includes: [
      "Services and price list",
      "Gallery of your work",
      "Booking on WhatsApp",
      "Link to your Instagram",
      "Timings, address and directions",
    ],
    packageId: "synex-starter-website",
    related: ["fieldofsoma", "idael-alfonso"],
  },
  {
    slug: "restaurants",
    plural: "Restaurants and cafes",
    singular: "restaurant",
    title: ["A restaurant website", "people actually use."],
    intro:
      "A menu that opens fast on any phone, photos that make people hungry, and one tap to reserve, order or find you.",
    includes: [
      "Menu that loads fast on phones",
      "Food and space photos",
      "Table booking or orders on WhatsApp",
      "Links to Zomato and Swiggy",
      "Hours, address and directions",
    ],
    packageId: "synex-starter-website",
    related: ["eve-pizzeria", "vento-tea"],
  },
  {
    slug: "gyms",
    plural: "Gyms",
    singular: "gym",
    title: ["A gym website", "that signs up members."],
    intro:
      "Plans, trainers and timings that are easy to compare, and a free trial request that lands on your WhatsApp.",
    includes: [
      "Membership plans and prices",
      "Trainer profiles",
      "Class schedule",
      "Free trial request on WhatsApp",
      "Location and timings",
    ],
    packageId: "synex-starter-website",
    related: ["idael-alfonso", "fieldofsoma"],
  },
  {
    slug: "coaching",
    plural: "Coaching centres",
    singular: "coaching centre",
    title: ["A coaching website", "parents trust."],
    intro:
      "Courses, batches, fees and faculty in one place, with an admission enquiry that comes straight to you.",
    includes: [
      "Courses, batches and timings",
      "Faculty profiles",
      "Results, shown with permission",
      "Admission enquiry on WhatsApp or a form",
      "Fees and contact details",
    ],
    packageId: "synex-starter-website",
    related: [],
  },
];

export const findNiche = (slug: string) => niches.find((n) => n.slug === slug);
