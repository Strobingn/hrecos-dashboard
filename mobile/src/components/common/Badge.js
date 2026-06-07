import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useTheme } from '../../hooks/useTheme';

export default function Badge({
  label,
  color,
  icon,
  size = 'medium',
  variant = 'filled',
}) {
  const theme = useTheme();

  const getSizeStyles = () => {
    switch (size) {
      case 'small':
        return {
          paddingHorizontal: 8,
          paddingVertical: 3,
          fontSize: 11,
          iconSize: 12,
          borderRadius: 10,
        };
      case 'large':
        return {
          paddingHorizontal: 16,
          paddingVertical: 7,
          fontSize: 15,
          iconSize: 18,
          borderRadius: 20,
        };
      case 'medium':
      default:
        return {
          paddingHorizontal: 12,
          paddingVertical: 5,
          fontSize: 13,
          iconSize: 14,
          borderRadius: 14,
        };
    }
  };

  const sizeStyles = getSizeStyles();
  const badgeColor = color || theme.colors.primary;

  const getVariantStyles = () => {
    if (variant === 'outlined') {
      return {
        backgroundColor: theme.colors.transparent,
        borderColor: badgeColor,
        borderWidth: 1.5,
        textColor: badgeColor,
      };
    }
    return {
      backgroundColor: badgeColor + '22',
      borderColor: theme.colors.transparent,
      borderWidth: 0,
      textColor: badgeColor,
    };
  };

  const variantStyles = getVariantStyles();

  if (!label && !icon) return null;

  return (
    <View
      style={[
        styles.badge,
        {
          backgroundColor: variantStyles.backgroundColor,
          borderColor: variantStyles.borderColor,
          borderWidth: variantStyles.borderWidth,
          borderRadius: sizeStyles.borderRadius,
          paddingHorizontal: sizeStyles.paddingHorizontal,
          paddingVertical: sizeStyles.paddingVertical,
        },
      ]}
    >
      {icon && (
        <MaterialCommunityIcons
          name={icon}
          size={sizeStyles.iconSize}
          color={variantStyles.textColor}
          style={styles.icon}
        />
      )}
      {label && (
        <Text
          style={[
            styles.label,
            {
              fontSize: sizeStyles.fontSize,
              color: variantStyles.textColor,
              fontWeight: variant === 'filled' ? '700' : '600',
            },
          ]}
        >
          {label}
        </Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
  },
  icon: {
    marginRight: 4,
  },
  label: {
    includeFontPadding: false,
  },
});
