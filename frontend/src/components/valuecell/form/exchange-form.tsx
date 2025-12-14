import { Wallet } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useTestConnection } from "@/api/strategy";
import { Button } from "@/components/ui/button";
import { FieldGroup } from "@/components/ui/field";
import { Label } from "@/components/ui/label";
import { RadioGroupItem } from "@/components/ui/radio-group";
import { SelectItem } from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import PngIcon from "@/components/valuecell/icon/png-icon";
import { EXCHANGE_ICONS } from "@/constants/icons";
import { withForm } from "@/hooks/use-form";

export const EXCHANGE_OPTIONS = [
  {
    value: "okx",
    label: "OKX",
  },
  {
    value: "binance",
    label: "Binance",
  },
  {
    value: "hyperliquid",
    label: "Hyperliquid",
  },
  {
    value: "blockchaincom",
    label: "Blockchain",
  },
  {
    value: "coinbaseexchange",
    label: "Coinbase",
  },
  {
    value: "gate",
    label: "Gate",
  },
  {
    value: "mexc",
    label: "MEXC",
  },
];

const getPlaceholder = (
  exchangeId: string,
  fieldType:
    | "api_key"
    | "secret_key"
    | "passphrase"
    | "wallet_address"
    | "private_key",
  t: (key: string) => string,
): string => {
  switch (exchangeId) {
    case "binance":
      if (fieldType === "api_key") return t("strategy.form.exchanges.placeholder.binance.apiKey");
      if (fieldType === "secret_key") return t("strategy.form.exchanges.placeholder.binance.secretKey");
      break;
    case "okx":
      if (fieldType === "api_key")
        return t("strategy.form.exchanges.placeholder.okx.apiKey");
      if (fieldType === "secret_key")
        return t("strategy.form.exchanges.placeholder.okx.secretKey");
      if (fieldType === "passphrase")
        return t("strategy.form.exchanges.placeholder.okx.passphrase");
      break;
    case "gate":
      if (fieldType === "api_key") return t("strategy.form.exchanges.placeholder.gate.apiKey");
      if (fieldType === "secret_key") return t("strategy.form.exchanges.placeholder.gate.secretKey");
      break;
    case "hyperliquid":
      if (fieldType === "wallet_address")
        return t("strategy.form.exchanges.placeholder.hyperliquid.walletAddress");
      if (fieldType === "private_key")
        return t("strategy.form.exchanges.placeholder.hyperliquid.privateKey");
      break;
    case "blockchaincom":
      if (fieldType === "api_key")
        return t("strategy.form.exchanges.placeholder.blockchain.apiKey");
      if (fieldType === "secret_key") return t("strategy.form.exchanges.placeholder.blockchain.secretKey");
      break;
    case "coinbaseexchange":
      if (fieldType === "api_key") return t("strategy.form.exchanges.placeholder.coinbase.apiKey");
      if (fieldType === "secret_key")
        return t("strategy.form.exchanges.placeholder.coinbase.secretKey");
      if (fieldType === "passphrase")
        return t("strategy.form.exchanges.placeholder.coinbase.passphrase");
      break;
    case "mexc":
      if (fieldType === "api_key")
        return t("strategy.form.exchanges.placeholder.mexc.apiKey");
      if (fieldType === "secret_key")
        return t("strategy.form.exchanges.placeholder.mexc.secretKey");
      break;
  }

  // Default placeholders
  if (fieldType === "api_key") return t("strategy.form.exchanges.placeholder.default.apiKey");
  if (fieldType === "secret_key") return t("strategy.form.exchanges.placeholder.default.secretKey");
  if (fieldType === "passphrase") return t("strategy.form.exchanges.placeholder.default.passphrase");
  if (fieldType === "wallet_address") return t("strategy.form.exchanges.placeholder.default.walletAddress");
  if (fieldType === "private_key") return t("strategy.form.exchanges.placeholder.default.privateKey");
  return "";
};

export const ExchangeForm = withForm({
  defaultValues: {
    trading_mode: "live" as "live" | "virtual",
    exchange_id: "",
    api_key: "",
    secret_key: "",
    passphrase: "",
    wallet_address: "",
    private_key: "",
  },
  render({ form }) {
    const { t } = useTranslation();
    const { mutateAsync: testConnection, isPending } = useTestConnection();
    const [testStatus, setTestStatus] = useState<{
      success: boolean;
      message: string;
    } | null>(null);

    const handleTestConnection = async () => {
      setTestStatus(null);
      try {
        await testConnection(form.state.values);
        setTestStatus({ success: true, message: t("strategy.form.exchanges.test.success") });
      } catch (_error) {
        setTestStatus({
          success: false,
          message: t("strategy.form.exchanges.test.failed"),
        });
      }
    };

    return (
      <FieldGroup className="gap-4">
        <form.AppField
          listeners={{
            onChange: ({ value }) => {
              form.reset({
                trading_mode: value,
                exchange_id: value === "live" ? "okx" : "",
                api_key: "",
                secret_key: "",
                passphrase: "",
                wallet_address: "",
                private_key: "",
              });
            },
          }}
          name="trading_mode"
        >
          {(field) => (
            <field.RadioField label={t("strategy.form.exchanges.transactionType")}>
              <div className="flex items-center gap-2">
                <RadioGroupItem value="live" id="live" />
                <Label htmlFor="live" className="text-sm">
                  {t("strategy.form.exchanges.liveTrading")}
                </Label>
              </div>
              <div className="flex items-center gap-2">
                <RadioGroupItem value="virtual" id="virtual" />
                <Label htmlFor="virtual" className="text-sm">
                  {t("strategy.form.exchanges.virtualTrading")}
                </Label>
              </div>
            </field.RadioField>
          )}
        </form.AppField>

        <form.Subscribe selector={(state) => state.values.trading_mode}>
          {(tradingMode) => {
            return (
              tradingMode === "live" && (
                <>
                  <form.AppField name="exchange_id">
                    {(field) => (
                      <field.SelectField label={t("strategy.form.exchanges.selectExchange")}>
                        {EXCHANGE_OPTIONS.map((option) => (
                          <SelectItem key={option.value} value={option.value}>
                            <div className="flex items-center gap-2">
                              <PngIcon
                                src={
                                  EXCHANGE_ICONS[
                                    option.value as keyof typeof EXCHANGE_ICONS
                                  ]
                                }
                              />
                              {option.label}
                            </div>
                          </SelectItem>
                        ))}
                      </field.SelectField>
                    )}
                  </form.AppField>

                  <form.Subscribe
                    selector={(state) => state.values.exchange_id}
                  >
                    {(exchangeId) => {
                      return exchangeId === "hyperliquid" ? (
                        <>
                          <form.AppField name="wallet_address">
                            {(field) => (
                              <field.TextField
                                label={t("strategy.form.exchanges.walletAddress")}
                                placeholder={getPlaceholder(
                                  exchangeId || "",
                                  "wallet_address",
                                  t,
                                )}
                              />
                            )}
                          </form.AppField>
                          <form.AppField name="private_key">
                            {(field) => (
                              <field.PasswordField
                                label={t("strategy.form.exchanges.privateKey")}
                                placeholder={getPlaceholder(
                                  exchangeId || "",
                                  "private_key",
                                  t,
                                )}
                              />
                            )}
                          </form.AppField>
                        </>
                      ) : (
                        <>
                          <form.AppField name="api_key">
                            {(field) => (
                              <field.PasswordField
                                label={t("strategy.form.exchanges.apiKey")}
                                placeholder={getPlaceholder(
                                  exchangeId || "",
                                  "api_key",
                                  t,
                                )}
                              />
                            )}
                          </form.AppField>
                          <form.AppField name="secret_key">
                            {(field) => (
                              <field.PasswordField
                                label={t("strategy.form.exchanges.secretKey")}
                                placeholder={getPlaceholder(
                                  exchangeId || "",
                                  "secret_key",
                                  t,
                                )}
                              />
                            )}
                          </form.AppField>

                          {(exchangeId === "okx" ||
                            exchangeId === "coinbaseexchange") && (
                            <form.AppField name="passphrase">
                              {(field) => (
                                <field.PasswordField
                                  label={t("strategy.form.exchanges.passphrase")}
                                  placeholder={getPlaceholder(
                                    exchangeId || "",
                                    "passphrase",
                                    t,
                                  )}
                                />
                              )}
                            </form.AppField>
                          )}
                        </>
                      );
                    }}
                  </form.Subscribe>

                  <div className="-mt-2 flex flex-col gap-2">
                    {testStatus && (
                      <p
                        className={`font-medium text-sm ${
                          testStatus.success ? "text-green-600" : "text-red-600"
                        }`}
                      >
                        {testStatus.message}
                      </p>
                    )}
                    <Button
                      variant="outline"
                      className="w-full gap-2 py-4 font-medium text-base"
                      onClick={handleTestConnection}
                      disabled={isPending}
                      type="button"
                    >
                      {isPending ? (
                        <Spinner className="size-5 text-gray-500" />
                      ) : (
                        <Wallet className="size-5" />
                      )}
                      {t("strategy.form.exchanges.testConnection")}
                    </Button>
                  </div>
                </>
              )
            );
          }}
        </form.Subscribe>
      </FieldGroup>
    );
  },
});
