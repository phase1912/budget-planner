import enAdmin from "@/locales/en/admin.json";
import enAuth from "@/locales/en/auth.json";
import enCategories from "@/locales/en/categories.json";
import enCommon from "@/locales/en/common.json";
import enDashboard from "@/locales/en/dashboard.json";
import enErrors from "@/locales/en/errors.json";
import enGoals from "@/locales/en/goals.json";
import enHelp from "@/locales/en/help.json";
import enHousehold from "@/locales/en/household.json";
import enLanding from "@/locales/en/landing.json";
import enLegal from "@/locales/en/legal.json";
import enMessages from "@/locales/en/messages.json";
import enProducts from "@/locales/en/products.json";
import enProfile from "@/locales/en/profile.json";
import enReceipts from "@/locales/en/receipts.json";
import enStatistics from "@/locales/en/statistics.json";
import enTrips from "@/locales/en/trips.json";
import enPlan from "@/locales/en/plan.json";
import enUpload from "@/locales/en/upload.json";
import plAdmin from "@/locales/pl/admin.json";
import plAuth from "@/locales/pl/auth.json";
import plCategories from "@/locales/pl/categories.json";
import plCommon from "@/locales/pl/common.json";
import plDashboard from "@/locales/pl/dashboard.json";
import plErrors from "@/locales/pl/errors.json";
import plGoals from "@/locales/pl/goals.json";
import plHelp from "@/locales/pl/help.json";
import plHousehold from "@/locales/pl/household.json";
import plLanding from "@/locales/pl/landing.json";
import plLegal from "@/locales/pl/legal.json";
import plMessages from "@/locales/pl/messages.json";
import plProducts from "@/locales/pl/products.json";
import plProfile from "@/locales/pl/profile.json";
import plReceipts from "@/locales/pl/receipts.json";
import plStatistics from "@/locales/pl/statistics.json";
import plTrips from "@/locales/pl/trips.json";
import plPlan from "@/locales/pl/plan.json";
import plUpload from "@/locales/pl/upload.json";
import ukAdmin from "@/locales/uk/admin.json";
import ukAuth from "@/locales/uk/auth.json";
import ukCategories from "@/locales/uk/categories.json";
import ukCommon from "@/locales/uk/common.json";
import ukDashboard from "@/locales/uk/dashboard.json";
import ukErrors from "@/locales/uk/errors.json";
import ukGoals from "@/locales/uk/goals.json";
import ukHelp from "@/locales/uk/help.json";
import ukHousehold from "@/locales/uk/household.json";
import ukLanding from "@/locales/uk/landing.json";
import ukLegal from "@/locales/uk/legal.json";
import ukMessages from "@/locales/uk/messages.json";
import ukProducts from "@/locales/uk/products.json";
import ukProfile from "@/locales/uk/profile.json";
import ukReceipts from "@/locales/uk/receipts.json";
import ukStatistics from "@/locales/uk/statistics.json";
import ukTrips from "@/locales/uk/trips.json";
import ukPlan from "@/locales/uk/plan.json";
import ukUpload from "@/locales/uk/upload.json";

/**
 * Every translation, one file per screen area (F9.9). English is the source: its files
 * are what the keys are typed against, and `npm run lint:locales` fails the build when
 * Ukrainian or Polish lacks one of them. Generated from the files in src/locales/en.
 */
export const en = {
  admin: enAdmin,
  auth: enAuth,
  categories: enCategories,
  common: enCommon,
  dashboard: enDashboard,
  errors: enErrors,
  goals: enGoals,
  help: enHelp,
  household: enHousehold,
  landing: enLanding,
  legal: enLegal,
  messages: enMessages,
  products: enProducts,
  trips: enTrips,
  plan: enPlan,
  profile: enProfile,
  receipts: enReceipts,
  statistics: enStatistics,
  upload: enUpload,
};

export const resources = {
  en,
  uk: {
    admin: ukAdmin,
    auth: ukAuth,
    categories: ukCategories,
    common: ukCommon,
    dashboard: ukDashboard,
    errors: ukErrors,
    goals: ukGoals,
    help: ukHelp,
    household: ukHousehold,
    landing: ukLanding,
    legal: ukLegal,
    messages: ukMessages,
    products: ukProducts,
    trips: ukTrips,
    plan: ukPlan,
    profile: ukProfile,
    receipts: ukReceipts,
    statistics: ukStatistics,
    upload: ukUpload,
  },
  pl: {
    admin: plAdmin,
    auth: plAuth,
    categories: plCategories,
    common: plCommon,
    dashboard: plDashboard,
    errors: plErrors,
    goals: plGoals,
    help: plHelp,
    household: plHousehold,
    landing: plLanding,
    legal: plLegal,
    messages: plMessages,
    products: plProducts,
    trips: plTrips,
    plan: plPlan,
    profile: plProfile,
    receipts: plReceipts,
    statistics: plStatistics,
    upload: plUpload,
  },
} as const;
