using System;
using System.Security.Cryptography;
using System.Text;

namespace KspAutomationBridge
{
    /// <summary>Local bearer authentication. This file has no Unity/KSP dependencies.</summary>
    internal static class BridgeSecurity
    {
        public static string NewToken()
        {
            byte[] bytes = new byte[32];
            using (RandomNumberGenerator random = RandomNumberGenerator.Create())
            {
                random.GetBytes(bytes);
            }
            StringBuilder token = new StringBuilder(bytes.Length * 2);
            foreach (byte value in bytes)
            {
                token.Append(value.ToString("x2"));
            }
            return token.ToString();
        }

        public static bool IsAuthorized(string expectedToken, string authorization)
        {
            // The test host and deliberately unauthenticated integrations remain supported only
            // when no token was configured. The game plugin always creates one.
            if (string.IsNullOrEmpty(expectedToken))
            {
                return true;
            }
            if (string.IsNullOrEmpty(authorization) ||
                !authorization.StartsWith("Bearer ", StringComparison.Ordinal))
            {
                return false;
            }
            string presented = authorization.Substring(7);
            return presented.Length == expectedToken.Length && FixedTimeEquals(expectedToken, presented);
        }

        private static bool FixedTimeEquals(string expected, string presented)
        {
            int difference = 0;
            for (int i = 0; i < expected.Length; i++)
            {
                difference |= expected[i] ^ presented[i];
            }
            return difference == 0;
        }
    }
}
