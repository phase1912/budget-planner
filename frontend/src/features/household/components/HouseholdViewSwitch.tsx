import { observer } from "mobx-react-lite";

import { SegmentedControl } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";

/**
 * "Mine / <household>" on the dashboard and on Statistics (F12.5): which figures the
 * page shows. Absent until the household has someone to share with.
 */
export const HouseholdViewSwitch = observer(function HouseholdViewSwitch() {
  const { householdStore } = useStores();
  const household = householdStore.household;
  if (!household || !householdStore.shared) return null;
  return (
    <SegmentedControl
      label="Whose figures"
      value={householdStore.view}
      onChange={(view) => {
        householdStore.setView(view);
      }}
      fill
      options={[
        { value: "mine", label: "Mine" },
        { value: "household", label: household.name, shortLabel: "Household" },
      ]}
    />
  );
});
