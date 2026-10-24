import { Capacitor } from "@capacitor/core";

import type { Device } from "./device";
import { nativeDevice } from "./nativeDevice";
import { webDevice } from "./webDevice";

export type { Device, DeviceKind, FeltMoment, PhotoTaken } from "./device";

/** The device the client runs on, decided once at start. */
export const device: Device = Capacitor.isNativePlatform() ? nativeDevice() : webDevice;
