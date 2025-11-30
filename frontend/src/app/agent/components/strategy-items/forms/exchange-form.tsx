import { Wallet } from "lucide-react";
import { useState } from "react";
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
    const { mutateAsync: testConnection, isPending } = useTestConnection();
    const [testStatus, setTestStatus] = useState<{
      success: boolean;
      message: string;
    } | null>(null);

    const handleTestConnection = async () => {
      setTestStatus(null);
      try {
        await testConnection(form.state.values);
        setTestStatus({ success: true, message: "Success!" });
      } catch (_error) {
        setTestStatus({
          success: false,
          message: "Failed, please check your API key",
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
            <field.RadioField label="Transaction Type">
              <div className="flex items-center gap-2">
                <RadioGroupItem value="live" id="live" />
                <Label htmlFor="live" className="text-sm">
                  Live Trading
                </Label>
              </div>
              <div className="flex items-center gap-2">
                <RadioGroupItem value="virtual" id="virtual" />
                <Label htmlFor="virtual" className="text-sm">
                  Virtual Trading
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
                      <field.SelectField label="Select Exchange">
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
                                label="Wallet Address"
                                placeholder="Enter Main Wallet Address"
                              />
                            )}
                          </form.AppField>
                          <form.AppField name="private_key">
                            {(field) => (
                              <field.PasswordField
                                label="Private Key"
                                placeholder="Enter Wallet Private Key"
                              />
                            )}
                          </form.AppField>
                        </>
                      ) : (
                        <>
                          <form.AppField name="api_key">
                            {(field) => (
                              <field.PasswordField
                                label="API Key"
                                placeholder="Enter API Key"
                              />
                            )}
                          </form.AppField>
                          <form.AppField name="secret_key">
                            {(field) => (
                              <field.PasswordField
                                label="Secret Key"
                                placeholder="Enter Secret Key"
                              />
                            )}
                          </form.AppField>

                          {(exchangeId === "okx" ||
                            exchangeId === "coinbaseexchange") && (
                            <form.AppField name="passphrase">
                              {(field) => (
                                <field.PasswordField
                                  label="Passphrase"
                                  placeholder="Enter Passphrase"
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
                      Test Connection
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
