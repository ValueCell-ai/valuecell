import { useSignOut } from "@/api/system";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Field,
  FieldContent,
  FieldDescription,
  FieldGroup,
  FieldLabel,
  FieldTitle,
} from "@/components/ui/field";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import AppLoginModal from "@/components/valuecell/app/app-login-modal";
import { useTauriInfo } from "@/hooks/use-tauri-info";
import { useUpdateToast } from "@/hooks/use-update-toast";
import type { StockColorMode } from "@/store/settings-store";
import { useSettingsActions, useStockColorMode } from "@/store/settings-store";
import { useIsLoggedIn, useSystemInfo } from "@/store/system-store";

export default function GeneralPage() {
  const stockColorMode = useStockColorMode();
  const { setStockColorMode } = useSettingsActions();
  const { checkAndUpdate } = useUpdateToast();
  const { isTauriApp, appVersion } = useTauriInfo();
  const { email } = useSystemInfo();
  const isLoggedIn = useIsLoggedIn();

  const { mutate: signOut } = useSignOut();
  return (
    <div className="flex flex-1 flex-col gap-4 p-10">
      <div className="flex flex-col gap-1.5">
        <h1 className="font-bold text-gray-950 text-xl">General</h1>
        <p className="font-normal text-gray-500 text-sm">
          Manage your preferences and application settings
        </p>
      </div>

      <FieldGroup className="gap-6">
        {isTauriApp && (
          <Field orientation="horizontal">
            <FieldContent>
              <FieldTitle className="font-medium text-base text-gray-950">
                Account
              </FieldTitle>
              <FieldDescription>
                {isLoggedIn
                  ? email
                  : "Sign in to get started with Valuecell AI features."}
              </FieldDescription>
            </FieldContent>
            {isLoggedIn ? (
              <Button
                variant="outline"
                data-track="logout"
                onClick={() => signOut()}
              >
                Sign Out
              </Button>
            ) : (
              <AppLoginModal>
                <Button>Sign In</Button>
              </AppLoginModal>
            )}
          </Field>
        )}

        <Field orientation="horizontal">
          <FieldContent>
            <FieldTitle className="font-medium text-base text-gray-950">
              Quotes Color
            </FieldTitle>
            <FieldDescription>
              Choose how stock quote movements are visualized across the app.
            </FieldDescription>
          </FieldContent>
          <RadioGroup
            className="flex gap-3"
            value={stockColorMode}
            onValueChange={(value) =>
              setStockColorMode(value as StockColorMode)
            }
          >
            <FieldLabel
              className="flex cursor-pointer items-center space-x-3 text-nowrap rounded-lg border border-gray-200 p-3"
              htmlFor="green-up"
            >
              <RadioGroupItem value="GREEN_UP_RED_DOWN" id="green-up" />
              Green Up / Red Down
            </FieldLabel>
            <FieldLabel
              className="flex cursor-pointer items-center space-x-3 text-nowrap rounded-lg border border-gray-200 p-3"
              htmlFor="red-up"
            >
              <RadioGroupItem value="RED_UP_GREEN_DOWN" id="red-up" />
              Red Up / Green Down
            </FieldLabel>
          </RadioGroup>
        </Field>

        {isTauriApp && (
          <Field orientation="responsive">
            <FieldTitle className="flex items-center gap-2 font-medium text-base text-gray-950">
              App Updates
              {appVersion && <Badge variant="secondary">v{appVersion}</Badge>}
            </FieldTitle>
            <Button variant="outline" onClick={checkAndUpdate}>
              Check for Update
            </Button>
          </Field>
        )}
      </FieldGroup>
    </div>
  );
}
