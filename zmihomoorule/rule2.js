// Define main function (script entry)
function main(config, profileName) {
  // 用对象映射规则组
  const ruleGroups = {
    "DIRECT": [
      // stx365.com 主域名及子域名直连
      "stx365.com",
      "dev.stx365.com",

      // 常见 gov 结尾的国家或地区政府域名直连
      "gov",
      "gov.cn",
      "gov.hk",
      "gov.tw",
      "gov.sg",
      "gov.uk",
      "go.kr"
    ],

    "🔰国外流量": [
      // LinkedIn + Microsoft Copilot
      "linkedin.com",
      "licdn.com",
      "copilot.microsoft.com",

      // AWS 相关
      "freetier.us-east-1.api.aws",
      "secretsmanager.ap-east-1.amazonaws.com",
      "amazonaws.com",
      "aws.amazon.com"
    ]
  };

  // 统一生成规则
  Object.entries(ruleGroups).forEach(([policy, domains]) => {
    domains.forEach(domain => {
      config.rules.unshift(`DOMAIN-SUFFIX,${domain},${policy}`);
    });
  });

  return config;
}
