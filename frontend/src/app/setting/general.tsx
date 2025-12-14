import { useTranslation } from "react-i18next";
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
        <h1 className="font-bold text-gray-950 text-xl">
          {t("general.title")}
        </h1>
        <p className="font-normal text-gray-500 text-sm">
          {t("general.description")}
        </p>
      </div>

      <FieldGroup className="gap-6">
        {isTauriApp && (
          <Field orientation="horizontal">
            <FieldContent>
              <FieldTitle className="font-medium text-base text-gray-950">
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
            <FieldTitle className="font-medium text-base text-gray-950">
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
              <SelectItem value="en-US">English (United States)</SelectItem>
              <SelectItem value="en-GB">English (United Kingdom)</SelectItem>
              <SelectItem value="zh-Hans">简体中文</SelectItem>
              <SelectItem value="zh-Hant">繁體中文</SelectItem>
              <SelectItem value="ja-JP">日本語</SelectItem>
              <SelectItem value="de-DE">Deutsch</SelectItem>
              <SelectItem value="fr-FR">Français</SelectItem>
              <SelectItem value="ca-ES">Català</SelectItem>
              <SelectItem value="es-ES">Español</SelectItem>
              <SelectItem value="it-IT">Italiano</SelectItem>
              <SelectItem value="pl-PL">Polski</SelectItem>
              <SelectItem value="tr-TR">Türkçe</SelectItem>
              <SelectItem value="ru-RU">Русский</SelectItem>
              <SelectItem value="pt-PT">Português</SelectItem>
              <SelectItem value="id-ID">Bahasa Indonesia</SelectItem>
              <SelectItem value="ms-MY">Bahasa Melayu</SelectItem>
              <SelectItem value="th-TH">ภาษาไทย</SelectItem>
              <SelectItem value="vi-VN">Tiếng Việt</SelectItem>
              <SelectItem value="ko-KR">한국어</SelectItem>
            </SelectContent>
          </Select>
        </Field>

        <Field orientation="horizontal">
          <FieldContent>
            <FieldTitle className="font-medium text-base text-gray-950">
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
              className="flex cursor-pointer items-center space-x-3 text-nowrap rounded-lg border border-gray-200 p-3"
              htmlFor="green-up"
            >
              <RadioGroupItem value="GREEN_UP_RED_DOWN" id="green-up" />
              {t("general.quotesColor.greenUpRedDown")}
            </FieldLabel>
            <FieldLabel
              className="flex cursor-pointer items-center space-x-3 text-nowrap rounded-lg border border-gray-200 p-3"
              htmlFor="red-up"
            >
              <RadioGroupItem value="RED_UP_GREEN_DOWN" id="red-up" />
              {t("general.quotesColor.redUpGreenDown")}
            </FieldLabel>
          </RadioGroup>
        </Field>

        {isTauriApp && (
          <Field orientation="responsive">
            <FieldTitle className="flex items-center gap-2 font-medium text-base text-gray-950">
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
