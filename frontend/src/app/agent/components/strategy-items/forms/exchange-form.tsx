import { FieldGroup } from "@/components/ui/field";
import { Label } from "@/components/ui/label";
import { RadioGroupItem } from "@/components/ui/radio-group";
import { SelectItem } from "@/components/ui/select";
import PngIcon from "@/components/valuecell/png-icon";
import { EXCHANGE_ICONS } from "@/constants/icons";
import { withForm } from "@/hooks/use-form";

const EXCHANGE_OPTIONS = [
  {
    value: "okx",
    label: "OKX",
    icon: EXCHANGE_ICONS.okx,
  },
  {
    value: "binance",
    label: "Binance",
    icon: EXCHANGE_ICONS.binance,
  },
  {
    value: "hyperliquid",
    label: "Hyperliquid",
    icon: EXCHANGE_ICONS.hyperliquid,
  },
  {
    value: "blockchaincom",
    label: "Blockchain.com",
    icon: EXCHANGE_ICONS.blockchaincom,
  },
  {
    value: "coinbaseexchange",
    label: "Coinbase Exchange",
    icon: EXCHANGE_ICONS.coinbaseexchange,
  },
  {
    value: "gate",
    label: "Gate.io",
    icon: EXCHANGE_ICONS.gate,
  },
  {
    value: "mexc",
    label: "MEXC",
    icon: EXCHANGE_ICONS.mexc,
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
    return (
      <FieldGroup className="gap-6">
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
                              <PngIcon src={option.icon} />
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
                </>
              )
            );
          }}
        </form.Subscribe>
      </FieldGroup>
    );
  },
});
