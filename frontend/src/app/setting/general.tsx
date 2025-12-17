import { useTranslation } from "react-i18next";
import { useTheme } from "next-themes";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import LoginModal from "@/components/valuecell/modal/login-modal";
import { useTauriInfo } from "@/hooks/use-tauri-info";
import { useUpdateToast } from "@/hooks/use-update-toast";
import { withTrack } from "@/lib/tracker";
import type { LanguageCode, StockColorMode } from "@/store/settings-store";
import {
  useLanguage,
  useSettingsActions,
  useStockColorMode,
} from "@/store/settings-store";
import { useIsLoggedIn, useSystemInfo } from "@/store/system-store";

export default function GeneralPage() {
  const { t } = useTranslation();
  const { theme, setTheme } = useTheme();
  const stockColorMode = useStockColorMode();
  const language = useLanguage();
  const { setStockColorMode, setLanguage } = useSettingsActions();
  const { checkAndUpdate } = useUpdateToast();
  const { isTauriApp, appVersion } = useTauriInfo();
  const { email, id } = useSystemInfo();
  const isLoggedIn = useIsLoggedIn();

  const { mutate: signOut } = useSignOut();
  return (
    <div className="flex flex-1 flex-col gap-4 p-10">
      <div className="flex flex-col gap-1.5">
        <h1 className="font-bold text-xl">
          {t("general.title")}
        </h1>
        <p className="font-normal text-muted-foreground text-sm">
          {t("general.description")}
        </p>
      </div>

      <FieldGroup className="gap-6">
        {isTauriApp && (
          <Field orientation="horizontal">
            <FieldContent>
              <FieldTitle className="font-medium text-base">
                {t("general.account.title")}
              </FieldTitle>
              <FieldDescription>
                {isLoggedIn ? email : t("general.account.signInDesc")}
              </FieldDescription>
            </FieldContent>
            {isLoggedIn ? (
              <Button
                variant="outline"
                onClick={() => signOut()}
                {...withTrack("logout", { user_id: id })}
              >
                {t("general.account.signOut")}
              </Button>
            ) : (
              <LoginModal>
                <Button>{t("general.account.signIn")}</Button>
              </LoginModal>
            )}
          </Field>
        )}

        <Field orientation="horizontal">
          <FieldContent>
            <FieldTitle className="font-medium text-base">
              {t("general.language.title")}
            </FieldTitle>
            <FieldDescription>
              {t("general.language.description")}
            </FieldDescription>
          </FieldContent>
          <Select
            value={language}
            onValueChange={(value) => setLanguage(value as LanguageCode)}
          >
            <SelectTrigger className="w-[280px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="en">English (United States)</SelectItem>
              <SelectItem value="zh_CN">简体中文</SelectItem>
              <SelectItem value="zh_TW">繁體中文</SelectItem>
              <SelectItem value="ja">日本語</SelectItem>
            </SelectContent>
          </Select>
        </Field>

        <Field orientation="horizontal">
          <FieldContent>
            <FieldTitle className="font-medium text-base">
              {t("general.theme.title")}
            </FieldTitle>
            <FieldDescription>
              {t("general.theme.description")}
            </FieldDescription>
          </FieldContent>
          <Select
            value={theme ?? "system"}
            onValueChange={(value) => setTheme(value)}
          >
            <SelectTrigger className="w-[280px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="system">{t("general.theme.options.system")}</SelectItem>
              <SelectItem value="light">{t("general.theme.options.light")}</SelectItem>
              <SelectItem value="dark">{t("general.theme.options.dark")}</SelectItem>
            </SelectContent>
          </Select>
        </Field>

        <Field orientation="horizontal">
          <FieldContent>
            <FieldTitle className="font-medium text-base">
              {t("general.quotesColor.title")}
            </FieldTitle>
            <FieldDescription>
              {t("general.quotesColor.description")}
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
              className="flex cursor-pointer items-center space-x-3 text-nowrap rounded-lg border border-border p-3"
              htmlFor="green-up"
            >
              <RadioGroupItem value="GREEN_UP_RED_DOWN" id="green-up" />
              {t("general.quotesColor.greenUpRedDown")}
            </FieldLabel>
            <FieldLabel
              className="flex cursor-pointer items-center space-x-3 text-nowrap rounded-lg border border-border p-3"
              htmlFor="red-up"
            >
              <RadioGroupItem value="RED_UP_GREEN_DOWN" id="red-up" />
              {t("general.quotesColor.redUpGreenDown")}
            </FieldLabel>
          </RadioGroup>
        </Field>

        {isTauriApp && (
          <Field orientation="responsive">
            <FieldTitle className="flex items-center gap-2 font-medium text-base">
              {t("general.updates.title")}
              {appVersion && <Badge variant="secondary">v{appVersion}</Badge>}
            </FieldTitle>
            <Button variant="outline" onClick={checkAndUpdate}>
              {t("general.updates.check")}
            </Button>
          </Field>
        )}
      </FieldGroup>
    </div>
  );
}
